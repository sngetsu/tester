import requests
import re
import time
import random
import sys
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
URL_SITEMAP_INDEX = "https://missav.ws/sitemap.xml"
ARCHIVO_SALIDA = "playlist_missav_funcionando.m3u"
LIMITE_PAGINAS_A_REVISAR = 50 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://missav.ws/',
}

def obtener_sitemaps(url_index):
    try:
        resp = requests.get(url_index, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.content, 'xml')
        sitemaps = [loc.text for loc in soup.find_all('loc')]
        return sitemaps[::-1] 
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

def desempaquetar_javascript(html):
    """
    Busca el código packed de Dean Edwards (eval(function...)) 
    y reconstruye la URL de Surrit/MissAV.
    """
    try:
        # 1. Buscamos la lista de palabras clave dentro del eval()
        # El patrón busca: .split('|'),0,{}))
        # Y extrae el string largo antes de eso
        patron_packed = r"\}\('(.*?)'\.split\('\|'\)"
        match = re.search(patron_packed, html)
        
        if not match:
            return None
            
        # Obtenemos la lista de piezas "m3u8|uuid1|uuid2..."
        palabras = match.group(1).split('|')
        
        if "surrit" not in palabras and "missav" not in palabras:
            return None

        # 2. Lógica de reconstrucción del UUID
        # En el código que pasaste, las partes del UUID son hexadecimales.
        # Estructura UUID: 8-4-4-4-12 caracteres (ej: cf5b2853-c8ff-469d-bc96-8aeb25848073)
        
        part_8 = ""
        part_12 = ""
        part_4s = []

        # Recorremos las palabras para encontrar las piezas del rompecabezas
        for p in palabras:
            if re.match(r'^[0-9a-f]+$', p): # Solo si es hexadecimal
                if len(p) == 8:
                    part_8 = p
                elif len(p) == 12:
                    part_12 = p
                elif len(p) == 4:
                    part_4s.append(p)
        
        # MissAV suele poner los de 4 caracteres en orden inverso en la lista packed
        # Así que invertimos la lista de 4s para armar el UUID correctamente
        # Nota: Esto es heurística basada en el código fuente provisto.
        if part_8 and part_12 and len(part_4s) >= 3:
            # Orden asumido: 8 - 4(último encontrado) - 4(medio) - 4(primero) - 12
            uuid = f"{part_8}-{part_4s[2]}-{part_4s[1]}-{part_4s[0]}-{part_12}"
            
            return f"https://surrit.com/{uuid}/playlist.m3u8"
            
        return None

    except Exception as e:
        print(f"Error desempaquetando: {e}")
        return None

def procesar_pagina(url):
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

        # --- INTENTO 1: Búsqueda directa (por si acaso) ---
        video_url = ""
        patron_directo = r'https?:\\?\/\\?\/[^\s"\'<>]+\.m3u8'
        match_directo = re.search(patron_directo, html)
        
        if match_directo:
            video_url = match_directo.group(0).replace('\\', '')
        
        # --- INTENTO 2: Desempaquetado JS (La solución real) ---
        if not video_url or "surrit" not in video_url:
            video_url = desempaquetar_javascript(html)

        if video_url and "http" in video_url:
            print(f"   -> VIDEO ENCONTRADO: {video_url}")
            return f'#EXTINF:-1 tvg-logo="{imagen}" group-title="MissAV" type="movie",{titulo}\n{video_url}\n'
        
        return None
    except Exception as e:
        print(f"Error procesando {url}: {e}")
        return None

def main():
    print(f"--- INICIO: Buscando videos con decodificador JS ---")
    
    with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

    sitemaps = obtener_sitemaps(URL_SITEMAP_INDEX)
    total_revisados = 0 

    for sitemap in sitemaps:
        print(f"📂 Sitemap: {sitemap}")
        urls = extraer_urls_del_xml(sitemap)
        
        for url_video in urls:
            if total_revisados >= LIMITE_PAGINAS_A_REVISAR:
                print(f"\n🛑 Límite de {LIMITE_PAGINAS_A_REVISAR} páginas alcanzado.")
                sys.exit()

            # Filtro opcional
            if "uncensored" not in url_video.lower():
                total_revisados += 1
                continue

            print(f"[{total_revisados + 1}] Analizando: {url_video}")
            
            linea = procesar_pagina(url_video)
            if linea:
                with open(ARCHIVO_SALIDA, "a", encoding="utf-8") as f:
                    f.write(linea)
            else:
                print("   -> No se pudo extraer video.")
            
            total_revisados += 1
            time.sleep(1) 

if __name__ == "__main__":
    main()
