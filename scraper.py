import requests
import re
import time
import random
import sys
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
URL_SITEMAP_INDEX = "https://missav.ws/sitemap.xml"
ARCHIVO_SALIDA = "playlist_test_50.m3u"
LIMITE_PAGINAS_A_REVISAR = 50  # <--- SE DETIENE AL TOCAR 50 LINKS

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://missav.ws/',
}

def obtener_sitemaps(url_index):
    try:
        resp = requests.get(url_index, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        sitemaps = [loc.text for loc in soup.find_all('loc')]
        return sitemaps[::-1] # Empezar por el final (más nuevos)
    except:
        return []

def extraer_urls_del_xml(url_xml):
    try:
        resp = requests.get(url_xml, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        urls = [loc.text for loc in soup.find_all('loc')]
        return urls
    except:
        return []

def procesar_pagina(url):
    try:
        # Petición a la página
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return None
        
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # Extraer datos
        meta_title = soup.find('meta', property='og:title')
        titulo = meta_title['content'] if meta_title else "Unknown"
        titulo = titulo.replace(',', ' ').strip()

        meta_img = soup.find('meta', property='og:image')
        imagen = meta_img['content'] if meta_img else ""

        # Buscar m3u8
        patron = r'https?:\\?\/\\?\/[^\s"\'<>]+\.m3u8'
        match = re.search(patron, html)
        
        if match:
            video_url = match.group(0).replace('\\', '')
            if "http" in video_url:
                return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="MissAV" type="movie",{titulo}\n{video_url}\n'
        
        return None
    except:
        return None

def main():
    print(f"--- INICIO: Revisaré exactamente {LIMITE_PAGINAS_A_REVISAR} páginas del sitemap ---")
    
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    sitemaps = obtener_sitemaps(URL_SITEMAP_INDEX)
    
    total_revisados = 0 # Contador global de intentos

    for sitemap in sitemaps:
        print(f"📂 Abriendo lista: {sitemap}")
        urls = extraer_urls_del_xml(sitemap)
        
        for url_video in urls:
            # --- CONDICIÓN DE PARADA ABSOLUTA ---
            if total_revisados >= LIMITE_PAGINAS_A_REVISAR:
                print(f"\n🛑 LÍMITE ALCANZADO: Se revisaron {total_revisados} páginas.")
                print(f"✅ Revisa el archivo {ARCHIVO_SALIDA}")
                sys.exit() # Cierra el programa inmediatamente

            # Filtro opcional (puedes quitarlo si quieres ver todo lo que encuentre en esas 50)
            if "uncensored" not in url_video.lower():
                # Aunque lo saltemos, cuenta como página revisada del sitemap
                total_revisados += 1
                # print(f"Saltando (no uncensored) - {total_revisados}") 
                continue

            print(f"[{total_revisados + 1}/{LIMITE_PAGINAS_A_REVISAR}] Procesando: {url_video}")
            
            linea = procesar_pagina(url_video)
            if linea:
                with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f:
                    f.write(linea)
            
            total_revisados += 1
            time.sleep(1) # Pequeña pausa

if __name__ == "__main__":
    main()
