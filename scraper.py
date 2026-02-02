import requests
import re
import time
import random
import sys
import os
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
ARCHIVO_SALIDA = "playlist_missav.m3u"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://missav.ws/',
}

def extraer_urls_del_xml(url_xml):
    print(f"📂 Leyendo XML: {url_xml}")
    try:
        resp = requests.get(url_xml, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        
        # Detectar si es un índice de sitemaps (contiene <sitemap>) en lugar de urls
        if soup.find('sitemap'):
            print("❌ ERROR: Has introducido el sitemap INDICE (el principal).")
            print("👉 Por favor, usa uno de los sitemaps de items, ejemplo: https://missav.ws/sitemap_items_477.xml")
            return []

        urls = [loc.text for loc in soup.find_all('loc')]
        return urls
    except Exception as e:
        print(f"Error leyendo XML: {e}")
        return []

def desempaquetar_javascript(html):
    """
    Desencripta el código packed de Dean Edwards para sacar la URL de Surrit.
    """
    try:
        patron_packed = r"\}\('(.*?)'\.split\('\|'\)"
        match = re.search(patron_packed, html)
        
        if not match: return None
            
        palabras = match.group(1).split('|')
        
        if "surrit" not in palabras and "missav" not in palabras: return None

        # Reconstrucción heurística del UUID
        part_8, part_12 = "", ""
        part_4s = []

        for p in palabras:
            if re.match(r'^[0-9a-f]+$', p):
                if len(p) == 8: part_8 = p
                elif len(p) == 12: part_12 = p
                elif len(p) == 4: part_4s.append(p)
        
        if part_8 and part_12 and len(part_4s) >= 3:
            uuid = f"{part_8}-{part_4s[2]}-{part_4s[1]}-{part_4s[0]}-{part_12}"
            return f"https://surrit.com/{uuid}/playlist.m3u8"
            
        return None
    except:
        return None

def procesar_pagina(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return None
        
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # Título y Foto
        meta_title = soup.find('meta', property='og:title')
        titulo = meta_title['content'] if meta_title else "Unknown"
        titulo = titulo.replace(',', ' ').strip() # Limpiar comas para M3U
        
        meta_img = soup.find('meta', property='og:image')
        imagen = meta_img['content'] if meta_img else ""

        # Buscar Video (Desempaquetado JS)
        video_url = desempaquetar_javascript(html)

        # Si falla el JS, intentar búsqueda directa por si acaso
        if not video_url:
            match_directo = re.search(r'https?:\\?\/\\?\/[^\s"\'<>]+\.m3u8', html)
            if match_directo:
                video_url = match_directo.group(0).replace('\\', '')

        if video_url and "http" in video_url:
            print(f"   ✅ OK: {titulo[:40]}...")
            return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="MissAV" type="movie",{titulo}\n{video_url}\n'
        
        return None
    except Exception as e:
        print(f"   ❌ Error procesando: {e}")
        return None

def main():
    target_sitemap = os.getenv('TARGET_SITEMAP')
    
    if not target_sitemap:
        print("❌ Error: No se ingresó ninguna URL de Sitemap.")
        sys.exit(1)

    print(f"--- INICIO: Procesando {target_sitemap} SIN FILTROS ---")
    
    urls = extraer_urls_del_xml(target_sitemap)
    
    if not urls:
        print("⚠️ No se encontraron URLs o el archivo es incorrecto.")
        sys.exit(1)

    print(f"📊 Total de videos a procesar: {len(urls)}")
    
    with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f:
        # Escribir cabecera solo si el archivo es nuevo
        if not os.path.exists(ARCHIVO_SALIDA) or os.stat(ARCHIVO_SALIDA).st_size == 0:
            f.write("#EXTM3U\n")

        count = 0
        for url_video in urls:
            count += 1
            print(f"[{count}/{len(urls)}] {url_video} ...", end=" ")
            
            linea = procesar_pagina(url_video)
            
            if linea:
                f.write(linea)
                f.flush()
            else:
                print("⚠️ Sin video")
            
            # Pausa pequeña
            time.sleep(random.uniform(0.5, 1.5))

if __name__ == "__main__":
    main()
