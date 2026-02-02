import requests
import re
import time
import random
import sys
import os
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
CARPETA_SALIDA = "playlists"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://missav.ws/',
    'Accept-Language': 'en-US,en;q=0.9', # Forzamos inglés
    'Cookie': 'language=en'
}

def obtener_ruta_archivo(nombre_base, inicio, fin):
    """Genera: playlists/uncensored_p1-p5.m3u"""
    clean_name = re.sub(r'\W+', '_', nombre_base).strip('_')
    nombre_archivo = f"playlist_{clean_name}_p{inicio}-p{fin}.m3u"
    return os.path.join(CARPETA_SALIDA, nombre_archivo)

def desempaquetar_javascript(html):
    """Lógica de desencriptado (Mismo método que ya funciona)"""
    try:
        patron_packed = r"\}\('(.*?)'\.split\('\|'\)"
        match = re.search(patron_packed, html)
        if not match: return None
        palabras = match.group(1).split('|')
        
        # Heurística MissAV
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

def extraer_video_final(url_video):
    """Entra a la página del video y saca el m3u8"""
    try:
        # Forzar URL en inglés para títulos limpios
        if "/th/" in url_video: url_video = url_video.replace("/th/", "/en/")
        elif "/es/" in url_video: url_video = url_video.replace("/es/", "/en/")
        
        resp = requests.get(url_video, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return None
        
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # Metadatos
        meta_title = soup.find('meta', property='og:title')
        titulo = meta_title['content'] if meta_title else "Unknown"
        titulo = titulo.replace(',', ' ').strip()
        
        meta_img = soup.find('meta', property='og:image')
        imagen = meta_img['content'] if meta_img else ""

        # Desencriptar
        video_url = desempaquetar_javascript(html)
        
        if video_url:
            return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="MissAV Page" type="movie",{titulo}\n{video_url}\n'
        return None
    except:
        return None

def procesar_listado_pagina(url_categoria):
    """Obtiene los links de los videos de una página de categoría (Grid)"""
    print(f"   🔎 Escaneando galería: {url_categoria}")
    try:
        resp = requests.get(url_categoria, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        links = []
        # Buscamos los divs con clase 'thumbnail'
        thumbnails = soup.find_all('div', class_='thumbnail')
        
        for thumb in thumbnails:
            # Buscamos el tag 'a' que tiene la clase 'text-secondary' (suele ser el título abajo)
            # O el 'a' directo de la imagen
            enlace = thumb.find('a', href=True)
            if enlace:
                full_url = enlace['href']
                if "http" not in full_url: # Si es ruta relativa
                    full_url = "https://missav.ws" + full_url
                links.append(full_url)
        
        # Eliminar duplicados manteniendo orden
        return list(dict.fromkeys(links))
    except Exception as e:
        print(f"Error leyendo página: {e}")
        return []

def main():
    # 1. Obtener Inputs
    base_url = os.getenv('CATEGORY_URL')
    start_page = int(os.getenv('START_PAGE', 1))
    end_page = int(os.getenv('END_PAGE', 1))

    if not base_url:
        print("❌ Error: No se ingresó URL de categoría.")
        sys.exit(1)

    # Limpieza de URL (quitamos params viejos)
    base_url = base_url.split('?')[0]
    
    # Nombre de archivo basado en la última parte de la URL
    nombre_categoria = base_url.split('/')[-1] or "missav_custom"
    
    # Crear carpeta
    if not os.path.exists(CARPETA_SALIDA):
        os.makedirs(CARPETA_SALIDA)
        
    archivo_destino = obtener_ruta_archivo(nombre_categoria, start_page, end_page)
    print(f"--- RANGO: {start_page} a {end_page} | CATEGORÍA: {nombre_categoria} ---")
    print(f"💾 Guardando en: {archivo_destino}")

    with open(archivo_destino, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        # 2. Bucle por páginas
        for page_num in range(start_page, end_page + 1):
            url_pag = f"{base_url}?page={page_num}"
            print(f"\n📄 Procesando Página {page_num}/{end_page}...")
            
            video_links = procesar_listado_pagina(url_pag)
            print(f"   -> Encontrados {len(video_links)} videos.")
            
            # 3. Bucle por videos dentro de la página
            for i, vid_url in enumerate(video_links):
                print(f"      [{i+1}/{len(video_links)}] Extrayendo...", end=" ")
                linea = extraer_video_final(vid_url)
                
                if linea:
                    print("✅")
                    f.write(linea)
                    f.flush()
                else:
                    print("❌")
                
                # Pausa leve entre videos para no saturar
                time.sleep(random.uniform(0.5, 1.0))
            
            # Pausa mayor entre páginas
            time.sleep(2)

if __name__ == "__main__":
    main()
