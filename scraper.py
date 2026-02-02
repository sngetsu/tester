import requests
import re
import time
import random
import sys
import os
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
# Headers con idioma forzado a Inglés para evitar títulos en Portugués
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://missav.ws/',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cookie': 'language=en' 
}

def obtener_nombre_archivo(url_xml):
    """Genera un nombre de archivo único basado en la URL del sitemap"""
    # Ejemplo entrada: https://missav.ws/sitemap_items_477.xml
    # Ejemplo salida: playlist_items_477.m3u
    try:
        match = re.search(r'sitemap_(.*)\.xml', url_xml)
        if match:
            suffix = match.group(1) # items_477
            return f"playlist_{suffix}.m3u"
    except:
        pass
    return "playlist_general.m3u"

def extraer_urls_del_xml(url_xml):
    print(f"📂 Leyendo XML: {url_xml}")
    try:
        resp = requests.get(url_xml, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        
        if soup.find('sitemap'):
            print("❌ ERROR: Has introducido el sitemap ÍNDICE (el principal). Usa uno de items.")
            return []

        urls = [loc.text for loc in soup.find_all('loc')]
        return urls
    except Exception as e:
        print(f"Error leyendo XML: {e}")
        return []

def desempaquetar_javascript(html):
    try:
        patron_packed = r"\}\('(.*?)'\.split\('\|'\)"
        match = re.search(patron_packed, html)
        if not match: return None
        palabras = match.group(1).split('|')
        if "surrit" not in palabras and "missav" not in palabras: return None

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
        # Forzamos URL en inglés si no lo está
        if "/en/" not in url and "/dm" not in url: 
             url = url.replace("missav.ws/", "missav.ws/en/")

        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return None
        
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        meta_title = soup.find('meta', property='og:title')
        titulo = meta_title['content'] if meta_title else "Unknown"
        titulo = titulo.replace(',', ' ').strip()
        
        meta_img = soup.find('meta', property='og:image')
        imagen = meta_img['content'] if meta_img else ""

        video_url = desempaquetar_javascript(html)
        if not video_url:
            match_directo = re.search(r'https?:\\?\/\\?\/[^\s"\'<>]+\.m3u8', html)
            if match_directo:
                video_url = match_directo.group(0).replace('\\', '')

        if video_url and "http" in video_url:
            print(f"   ✅ OK: {titulo[:40]}...")
            return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="MissAV" type="movie",{titulo}\n{video_url}\n'
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    target_sitemap = os.getenv('TARGET_SITEMAP')
    
    if not target_sitemap:
        print("❌ Error: No URL.")
        sys.exit(1)

    # --- CAMBIO IMPORTANTE: NOMBRE DINÁMICO ---
    archivo_salida = obtener_nombre_archivo(target_sitemap)
    print(f"--- INICIO: Guardando en {archivo_salida} ---")
    
    urls = extraer_urls_del_xml(target_sitemap)
    
    if not urls: sys.exit(1)

    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n") # Usamos "w" para crear archivo nuevo limpio para ESTA lista

        count = 0
        for url_video in urls:
            count += 1
            print(f"[{count}/{len(urls)}] Procesando...", end=" ")
            linea = procesar_pagina(url_video)
            
            if linea:
                f.write(linea)
                f.flush()
            else:
                print("⚠️ Falló")
            
            time.sleep(random.uniform(0.5, 1))

if __name__ == "__main__":
    main()
