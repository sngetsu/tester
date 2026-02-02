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

        # Reconstrucción heurística del UUID (8-4-4-4-12)
        part_8, part_12 = "", ""
        part_4s = []

        for p in palabras:
            if re.match(r'^[0-9a-f]+$', p):
                if len(p) == 8: part_8 = p
                elif len(p) == 12: part_12 = p
                elif len(p) == 4: part_4s.append(p)
        
        # MissAV suele invertir el orden de los bloques de 4 caracteres
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
        titulo = titulo.replace(',', ' ').strip()
        
        meta_img = soup.find('meta', property='og:image')
        imagen = meta_img['content'] if meta_img else ""

        # Buscar Video
        video_url = ""
        # Intento 1: Regex simple
        match_directo = re.search(r'https?:\\?\/\\?\/[^\s"\'<>]+\.m3u8', html)
        if match_directo:
            video_url = match_directo.group(0).replace('\\', '')
        
        # Intento 2: Desempaquetado JS
        if not video_url or "surrit" not in video_url:
            video_url = desempaquetar_javascript(html)

        if video_url and "http" in video_url:
            print(f"   ✅ OK: {titulo[:30]}...")
            return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="MissAV" type="movie",{titulo}\n{video_url}\n'
        
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    # 1. Obtener la URL ingresada manualmente desde GitHub Actions
    target_sitemap = os.getenv('TARGET_SITEMAP')
    
    if not target_sitemap:
        print("❌ Error: No se ingresó ninguna URL de Sitemap.")
        sys.exit(1)

    print(f"--- INICIO: Procesando bloque completo: {target_sitemap} ---")
    
    # Modo "Append" ('a') para no borrar lo que ya tenías guardado de ejecuciones anteriores
    with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f:
        # Si el archivo está vacío, escribimos la cabecera
        if os.stat(ARCHIVO_SALIDA).st_size == 0:
            f.write("#EXTM3U\n")

        urls = extraer_urls_del_xml(target_sitemap)
        print(f"📊 Total de videos en este XML: {len(urls)}")
        
        count = 0
        for url_video in urls:
            count += 1
            
            # Filtro opcional (puedes quitarlo si quieres todo)
            if "uncensored" not in url_video.lower():
                print(f"[{count}/{len(urls)}] Saltado (Censurado)")
                continue

            print(f"[{count}/{len(urls)}] Procesando...", end=" ")
            linea = procesar_pagina(url_video)
            
            if linea:
                f.write(linea)
                f.flush() # Guardar inmediatamente en disco
            else:
                print("   ⚠️ No se pudo extraer.")
            
            # Pausa pequeña para ser educado con el servidor
            time.sleep(1) 

if __name__ == "__main__":
    main()
