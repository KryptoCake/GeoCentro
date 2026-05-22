import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
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
                    
                country = get_country_from_desc(description)
                
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
                    pais=country
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
                        
    print(f"Scraping finalizado. Se agregaron {new_sismos_count} nuevos sismos.")
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

if __name__ == "__main__":
    database.init_db()
    scrape_sismos()
    seed_initial_news()
