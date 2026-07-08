import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import urllib3
import database

# Suppress insecure request warnings due to verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Regex for parsing INETER earthquake lines
# Format: Date Time Lat Lon Depth Mag Type Location
# Example: 26/05/20 09:57:00 11.288 -87.401   7 3.0 <span class='estiloC'>C</span> 111 Km al suroeste de Masachapa, Nicaragua
sismo_regex = re.compile(
    r'^\s*(\d{2}/\d{2}/\d{2})\s+'           # 1: Date (YY/MM/DD)
    r'(\d{2}:\d{2}:\d{2})\s+'               # 2: Time (HH:MM:SS)
    r'(-?\d+\.\d+)\s+'                      # 3: Latitude
    r'(-?\d+\.\d+)\s+'                      # 4: Longitude
    r'(\d+)\s+'                             # 5: Depth (Profundidad)
    r'(\d+\.\d+)\s+'                        # 6: Magnitude
    r'(?:<span[^>]*>)?([A-Za-z])(?:</span>)?\s+' # 7: Type/Class
    r'(.*)$'                                # 8: Description
)

def clean_html_tags(text):
    # Remove any stray html tags like </span> or <pre>
    return re.sub(r'<[^>]+>', '', text).strip()

def get_country_from_desc(desc):
    desc_lower = desc.lower().strip()
    if 'nicaragua' in desc_lower:
        return 'Nicaragua'
    elif 'el salvador' in desc_lower:
        return 'El Salvador'
    elif 'guatemala' in desc_lower:
        return 'Guatemala'
    elif 'honduras' in desc_lower:
        return 'Honduras'
    elif 'costa rica' in desc_lower:
        return 'Costa Rica'
    elif 'panama' in desc_lower or 'panamá' in desc_lower:
        return 'Panamá'
    else:
        return 'Otros'

def scrape_ovsicori_recientes():
    url = "https://www.ovsicori.una.ac.cr/sistemas/sentidos_map/indexleqs.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    print(f"[{datetime.now()}] Iniciando scraping de sismos recientes de OVSICORI desde: {url}")
    new_count = 0
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code != 200:
            print(f"Error al obtener página de OVSICORI recientes. Código: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Excepción al conectar con OVSICORI recientes: {e}")
        return 0
        
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print("No se encontró la tabla de sismos recientes de OVSICORI.")
        return 0
        
    rows = table.find_all('tr')
    for row in rows[1:]: # skip header
        cells = row.find_all('td')
        if len(cells) < 7:
            continue
            
        # Headers: Fecha, Hora, Magnitud, Profundidad, Latitud, Longitud, Localizacion
        fecha = cells[0].get_text(strip=True)
        hora = cells[1].get_text(strip=True)
        magnitud_str = cells[2].get_text(strip=True)
        profundidad_str = cells[3].get_text(strip=True)
        latitud_str = cells[4].get_text(strip=True)
        longitud_str = cells[5].get_text(strip=True)
        descripcion = cells[6].get_text(strip=True)
        
        try:
            # Clean values
            magnitud = float(magnitud_str)
            profundidad = int(profundidad_str)
            latitud = float(latitud_str)
            longitud = float(longitud_str)
            
            try:
                date_obj = datetime.strptime(fecha, '%Y-%m-%d')
                fecha_formatted = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                fecha_formatted = fecha
                
            country = database.determinar_pais_coordenadas(latitud, longitud, descripcion)
                
            inserted = database.save_sismo(
                fecha_utc=fecha_formatted,
                hora_utc=hora,
                latitud=latitud,
                longitud=longitud,
                profundidad=profundidad,
                magnitud=magnitud,
                tipo='CR_REC',
                descripcion=descripcion,
                agencia='OVSICORI',
                feed='OVSICORI_REC',
                scraped_at=int(datetime.now(timezone.utc).timestamp())
            )
            
            if inserted:
                new_count += 1
                if magnitud >= 4.0:
                    alert_title = f"Sismo Reciente de magnitud {magnitud} en {country}"
                    if magnitud >= 5.0:
                        alert_title = f"ALERTA: Sismo Fuerte de magnitud {magnitud} en {country}"
                        
                    alert_desc = f"Un evento sísmico de magnitud {magnitud} Mw ocurrió el {fecha_formatted} a las {hora} (hora local/red), localizado a una profundidad de {profundidad} km. Referencia: {descripcion}."
                    database.save_news(
                        titulo=alert_title,
                        url=f"#{fecha_formatted}_{hora.replace(':', '')}",
                        fecha=fecha_formatted,
                        resumen=alert_desc,
                        pais=country
                    )
        except Exception as e:
            # Silently ignore format parsing errors on malformed rows
            pass
            
    print(f"Scraping de OVSICORI recientes finalizado. Se agregaron {new_count} nuevos sismos.")
    return new_count

def scrape_ovsicori_sentidos():
    url = "https://www.ovsicori.una.ac.cr/sistemas/sentidos_map/index.php?tipo=center"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    print(f"[{datetime.now()}] Iniciando scraping de sismos sentidos de OVSICORI desde: {url}")
    new_count = 0
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code != 200:
            print(f"Error al obtener página de OVSICORI sentidos. Código: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Excepción al conectar con OVSICORI sentidos: {e}")
        return 0
        
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print("No se encontró la tabla de sismos sentidos de OVSICORI.")
        return 0
        
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) != 10:
            continue
            
        # Headers: Fecha, Hora, Magnitud, Profundidad, Localizacion, Origen/Mecanismo, Reportado/Intensidad, Latitud, Longitud
        fecha = cells[0].get_text(strip=True)
        hora = cells[1].get_text(strip=True)
        magnitud_str = cells[2].get_text(strip=True)
        profundidad_str = cells[3].get_text(strip=True)
        localizacion = cells[4].get_text(strip=True)
        origen = cells[5].get_text(strip=True)
        reportes = cells[6].get_text(strip=True)
        latitud_str = cells[7].get_text(strip=True)
        longitud_str = cells[8].get_text(strip=True)
        
        if fecha == "Fecha" or "Magnitud" in magnitud_str:
            continue
            
        try:
            # Clean values
            magnitud = float(magnitud_str)
            profundidad = int(profundidad_str)
            latitud = float(latitud_str)
            longitud = float(longitud_str)
            
            try:
                date_obj = datetime.strptime(fecha, '%Y-%m-%d')
                fecha_formatted = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                fecha_formatted = fecha
                
            descripcion = f"{localizacion} (Origen: {origen}"
            if reportes:
                descripcion += f", Sentido en: {reportes}"
            descripcion += ")"
            
            country = database.determinar_pais_coordenadas(latitud, longitud, descripcion)
            
            inserted = database.save_sismo(
                fecha_utc=fecha_formatted,
                hora_utc=hora,
                latitud=latitud,
                longitud=longitud,
                profundidad=profundidad,
                magnitud=magnitud,
                tipo='CR_SEN',
                descripcion=descripcion,
                agencia='OVSICORI',
                feed='OVSICORI_SEN',
                scraped_at=int(datetime.now(timezone.utc).timestamp())
            )
            
            if inserted:
                new_count += 1
                alert_title = f"Sismo Sentido de magnitud {magnitud} en {country}"
                if magnitud >= 5.0:
                    alert_title = f"ALERTA: Sismo Fuerte Sentido de magnitud {magnitud} en {country}"
                    
                alert_desc = f"Sismo SENTIDO de magnitud {magnitud} Mw registrado el {fecha_formatted} a las {hora}. Referencia: {descripcion}."
                database.save_news(
                    titulo=alert_title,
                    url=f"#{fecha_formatted}_{hora.replace(':', '')}",
                    fecha=fecha_formatted,
                    resumen=alert_desc,
                    pais=country
                )
        except Exception as e:
            pass
            
    print(f"Scraping de OVSICORI sentidos finalizado. Se agregaron {new_count} nuevos sismos.")
    return new_count

def scrape_sismos():
    url = "https://webserver2.ineter.gob.ni/geofisica/sis/events/sismos.php"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"[{datetime.now()}] Iniciando scraping de sismos desde: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code != 200:
            print(f"Error al obtener página de INETER. Código de estado: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Excepción al conectar con INETER: {e}")
        return 0
        
    soup = BeautifulSoup(response.text, 'html.parser')
    anchors = soup.find_all('a')
    
    new_sismos_count = 0
    for anchor in anchors:
        href = anchor.get('href', '')
        if 'javascript:ver_mapa' in href:
            pre_tag = anchor.find('pre')
            if not pre_tag:
                raw_text = anchor.decode_contents()
            else:
                raw_text = pre_tag.decode_contents()
                
            # Clean raw text from multiple spaces and newlines
            clean_text = raw_text.replace('\n', ' ').replace('\r', ' ').strip()
            
            # Match regex
            match = sismo_regex.match(clean_text)
            if match:
                date_yy = match.group(1)
                time_hh = match.group(2)
                lat = float(match.group(3))
                lon = float(match.group(4))
                depth = int(match.group(5))
                magnitude = float(match.group(6))
                sismo_type = match.group(7)
                description = clean_html_tags(match.group(8))
                
                # Format date to YYYY-MM-DD
                try:
                    date_formatted = datetime.strptime(date_yy, '%y/%m/%d').strftime('%Y-%m-%d')
                except ValueError:
                    date_formatted = "20" + date_yy.replace('/', '-')
                    
                country = database.determinar_pais_coordenadas(lat, lon, description)
                
                # Save to database
                inserted = database.save_sismo(
                    fecha_utc=date_formatted,
                    hora_utc=time_hh,
                    latitud=lat,
                    longitud=lon,
                    profundidad=depth,
                    magnitud=magnitude,
                    tipo=sismo_type,
                    descripcion=description,
                    agencia='INETER',
                    feed='INETER',
                    scraped_at=int(datetime.now(timezone.utc).timestamp())
                )
                
                if inserted:
                    new_sismos_count += 1
                    # If it's a significant earthquake (mag >= 4.0), generate a news alert!
                    if magnitude >= 4.0:
                        alert_title = f"Sismo Moderado de magnitud {magnitude} detectado"
                        if magnitude >= 5.0:
                            alert_title = f"ALERTA: Sismo Fuerte de magnitud {magnitude} detectado"
                            
                        alert_desc = f"Un evento sísmico de magnitud {magnitude} Mw ocurrió el {date_formatted} a las {time_hh} UTC, localizado a una profundidad de {depth} km en {description}."
                        database.save_news(
                            titulo=alert_title,
                            url=f"#{date_formatted}_{time_hh.replace(':', '')}",
                            fecha=date_formatted,
                            resumen=alert_desc,
                            pais=country
                        )
                        
    # Now scrape Costa Rica sismos
    try:
        new_sismos_count += scrape_ovsicori_recientes()
    except Exception as e:
        print(f"Error en scrape_ovsicori_recientes: {e}")
        
    try:
        new_sismos_count += scrape_ovsicori_sentidos()
    except Exception as e:
        print(f"Error en scrape_ovsicori_sentidos: {e}")

    print(f"Scraping total finalizado. Se agregaron {new_sismos_count} nuevos sismos.")
    return new_sismos_count

def seed_initial_news():
    # Seeds initial educational/monitoring news if table is empty
    existing_news = database.get_news(limit=5)
    if not existing_news:
        initial_articles = [
            {
                'titulo': "Inicio del portal GeoCentro - Monitoreo Geológico de Centroamérica",
                'url': "#portal_start",
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'resumen': "Lanzamiento oficial de la plataforma piloto GeoCentro, dedicada a recopilar información en tiempo real sobre la actividad sísmica y volcánica de Centroamérica, comenzando con datos oficiales de Nicaragua.",
                'pais': "Nicaragua"
            },
            {
                'titulo': "Monitoreo del Volcán Masaya y sus niveles de desgasificación",
                'url': "#volcan_masaya",
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'resumen': "Científicos monitorean la actividad de desgasificación y el nivel del lago de lava en el cráter Santiago del Volcán Masaya. Los sensores reportan emisiones normales de dióxido de azufre.",
                'pais': "Nicaragua"
            },
            {
                'titulo': "El Cinturón de Fuego del Pacífico y la sismicidad en Centroamérica",
                'url': "#cinturon_fuego",
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'resumen': "Artículo educativo sobre por qué Centroamérica es una zona de alta actividad tectónica. La subducción de la placa de Cocos bajo la placa de Caribe es el motor principal de los terremotos de la región.",
                'pais': "Otros"
            }
        ]
        for article in initial_articles:
            database.save_news(
                titulo=article['titulo'],
                url=article['url'],
                fecha=article['fecha'],
                resumen=article['resumen'],
                pais=article['pais']
            )

def get_country_from_usgs_place(place):
    if not place:
        return "Otros"
    parts = place.split(',')
    if len(parts) > 1:
        country = parts[-1].strip()
        # Standardize United States
        if country.lower() in ['usa', 'u.s.', 'united states'] or len(country) == 2:
            return "Estados Unidos"
        return country
    
    # Fallback checks
    place_lower = place.lower()
    countries = ["nicaragua", "el salvador", "guatemala", "honduras", "costa rica", "panama", "panamá", "mexico", "méxico"]
    for c in countries:
        if c in place_lower:
            return c.title()
    return "Otros"

def fetch_usgs_sismos(period='day'):
    # period can be 'day' or 'week'
    url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_{period}.geojson"
    print(f"[{datetime.now()}] Iniciando descarga de sismos del USGS desde: {url}")
    new_count = 0
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            print(f"Error al obtener datos del USGS. Código: {response.status_code}")
            return 0
        data = response.json()
    except Exception as e:
        print(f"Excepción al conectar con USGS: {e}")
        return 0
    
    features = data.get('features', [])
    for feature in features:
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        
        usgs_id = feature.get('id')
        if not usgs_id:
            continue
            
        mag = properties.get('mag')
        if mag is None:
            continue
        try:
            mag = float(mag)
        except ValueError:
            continue
            
        place = properties.get('place') or "Ubicación desconocida"
        time_ms = properties.get('time')
        if not time_ms:
            continue
            
        url_detail = properties.get('url')
        mag_type = properties.get('magType')
        
        # Parse coordinates (GeoJSON is [longitude, latitude, depth])
        coords = geometry.get('coordinates', [])
        if len(coords) < 3:
            continue
        
        lon = coords[0]
        lat = coords[1]
        depth = coords[2]
        
        try:
            # Convert time
            dt = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)
            fecha_utc = dt.strftime('%Y-%m-%d')
            hora_utc = dt.strftime('%H:%M:%S')
            
            country = get_country_from_usgs_place(place)
            
            inserted = database.save_sismo_usgs(
                usgs_id=usgs_id,
                fecha_utc=fecha_utc,
                hora_utc=hora_utc,
                latitud=lat,
                longitud=lon,
                profundidad=depth,
                magnitud=mag,
                tipo_magnitud=mag_type,
                descripcion=place,
                pais=country,
                url=url_detail
            )
            if inserted:
                new_count += 1
        except Exception as e:
            pass
            
    print(f"Descarga de USGS finalizada. Se agregaron {new_count} nuevos sismos globales.")
    return new_count

def scrape_nhc_weather_alerts():
    feeds = {
        'Atlántico': 'https://www.nhc.noaa.gov/index-at.xml',
        'Pacífico Oriental': 'https://www.nhc.noaa.gov/index-ep.xml'
    }
    
    print(f"[{datetime.now()}] Iniciando descarga de alertas climáticas del NHC (NOAA)...")
    new_count = 0
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    import xml.etree.ElementTree as ET
    
    for basin, url in feeds.items():
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"Error al obtener alertas del NHC para {basin}. Código: {response.status_code}")
                continue
            root = ET.fromstring(response.content)
        except Exception as e:
            print(f"Excepción al conectar/parsear NHC {basin}: {e}")
            continue
            
        items = root.findall('.//item')
        for item in items:
            title_node = item.find('title')
            link_node = item.find('link')
            desc_node = item.find('description')
            pubdate_node = item.find('pubDate')
            
            if title_node is None or link_node is None:
                continue
                
            title = title_node.text.strip() if title_node.text else ""
            link = link_node.text.strip() if link_node.text else ""
            
            if not title or not link:
                continue
            
            description = ""
            if desc_node is not None and desc_node.text:
                description = desc_node.text.strip()
                description = clean_html_tags(description)
                if len(description) > 500:
                    description = description[:497] + "..."
            
            pub_date_str = ""
            if pubdate_node is not None and pubdate_node.text:
                pub_date_raw = pubdate_node.text.strip()
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_date_raw)
                    pub_date_str = dt.strftime('%Y-%m-%d')
                except Exception:
                    pub_date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                pub_date_str = datetime.now().strftime('%Y-%m-%d')
                
            country = "Otros"
            desc_lower = description.lower()
            title_lower = title.lower()
            
            countries_map = {
                'nicaragua': 'Nicaragua',
                'el salvador': 'El Salvador',
                'guatemala': 'Guatemala',
                'honduras': 'Honduras',
                'costa rica': 'Costa Rica',
                'panama': 'Panamá',
                'panamá': 'Panamá'
            }
            for key, val in countries_map.items():
                if key in desc_lower or key in title_lower:
                    country = val
                    break
            
            # Normalize URL to be absolute
            if link:
                link = link.strip()
                if not link.startswith('http'):
                    if link.startswith('/'):
                        link = "https://www.nhc.noaa.gov" + link
                    else:
                        link = "https://www.nhc.noaa.gov/" + link
            else:
                link = "https://www.nhc.noaa.gov/"

            inserted = database.save_news(
                titulo=f"[{basin}] {title}",
                url=link,
                fecha=pub_date_str,
                resumen=description,
                pais=country,
                categoria='clima'
            )
            if inserted:
                new_count += 1
                
    print(f"Descarga de alertas de clima finalizada. Se agregaron {new_count} boletines del NHC.")
    return new_count

if __name__ == "__main__":
    database.init_db()
    scrape_sismos()
    fetch_usgs_sismos('day')
    scrape_nhc_weather_alerts()
    seed_initial_news()
