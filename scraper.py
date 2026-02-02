import requests
import re
import time
import random
import sys
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
URL_SITEMAP_INDEX = "https://missav.ws/sitemap.xml"
ARCHIVO_SALIDA = "playlist_uncensored.m3u"
MAX_VIDEOS = 50  # <--- LÍMITE AGREGADO PARA PRUEBAS

# Headers para simular navegador real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://missav.ws/',
}

def obtener_sitemaps(url_index):
    try:
        resp = requests.get(url_index, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        sitemaps = [loc.text for loc in soup.find_all('loc')]
        # Invertimos para empezar por los más nuevos
        return sitemaps[::-1] 
    except Exception as e:
        print(f"Error obteniendo índice: {e}")
        return []

def extraer_urls_del_xml(url_xml):
    try:
        resp = requests.get(url_xml, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        urls = [loc.text for loc in soup.find_all('loc')]
        return urls
    except:
        return []

def procesar_video(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return None
        
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # Título
        meta_title = soup.find('meta', property='og:title')
        titulo = meta_title['content'] if meta_title else "Unknown"
        titulo = titulo.replace(',', ' ').strip() 

        # Imagen
        meta_img = soup.find('meta', property='og:image')
        imagen = meta_img['content'] if meta_img else ""

        # M3U8 (Regex)
        patron = r'https?:\\?\/\\?\/[^\s"\'<>]+\.m3u8'
        match = re.search(patron, html)
        
        if match:
            video_url = match.group(0).replace('\\', '')
            if "http" in video_url:
                return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="Uncensored" type="movie",{titulo}\n{video_url}\n'
        
        return None
    except:
        return None

def main():
    print(f"--- Iniciando Scraper (Límite: {MAX_VIDEOS} videos) ---")
    
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    sitemaps = obtener_sitemaps(URL_SITEMAP_INDEX)
    print(f"Se encontraron {len(sitemaps)} listas de sitemaps.")

    contador_videos = 0
    
    # Recorremos los sitemaps
    for sitemap in sitemaps:
        print(f"📂 Analizando sitemap: {sitemap}")
        urls = extraer_urls_del_xml(sitemap)
        
        for url_video in urls:
            # --- VERIFICACIÓN DE LÍMITE ---
            if contador_videos >= MAX_VIDEOS:
                print(f"\n🛑 ¡Límite de {MAX_VIDEOS} videos alcanzado! Finalizando script.")
                return # Detiene TODO el script inmediatamente

            # --- FILTRO MAESTRO ---
            if "uncensored" not in url_video.lower():
                continue
            
            print(f"[{contador_videos + 1}/{MAX_VIDEOS}] Procesando: {url_video}")
            linea_m3u = procesar_video(url_video)
            
            if linea_m3u:
                with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f:
                    f.write(linea_m3u)
                contador_videos += 1
            
            time.sleep(random.uniform(0.5, 1.5))

    print(f"--- Finalizado. Total videos: {contador_videos} ---")

if __name__ == "__main__":
    main()
