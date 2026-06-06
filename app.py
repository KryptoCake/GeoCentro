from flask import Flask, render_template, jsonify, request, Response
import requests
import urllib3
import database

# Suppress insecure request warnings due to verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Initialize database tables
database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/historical')
def historical():
    return render_template('historical.html')

@app.route('/tools')
def tools():
    return render_template('tools.html')

@app.route('/api/sismos')
def api_sismos():
    filters = {
        'pais': request.args.get('pais'),
        'min_magnitud': request.args.get('min_magnitud'),
        'max_magnitud': request.args.get('max_magnitud'),
        'profundidad_min': request.args.get('profundidad_min'),
        'profundidad_max': request.args.get('profundidad_max'),
        'fecha_inicio': request.args.get('fecha_inicio'),
        'fecha_fin': request.args.get('fecha_fin'),
        'buscar': request.args.get('buscar')
    }
    
    # Safely convert parameters
    for key in ['min_magnitud', 'max_magnitud']:
        if filters[key]:
            try:
                filters[key] = float(filters[key])
            except ValueError:
                filters[key] = None
                
    for key in ['profundidad_min', 'profundidad_max']:
        if filters[key]:
            try:
                filters[key] = int(filters[key])
            except ValueError:
                filters[key] = None
                
    limit = request.args.get('limit', 200)
    try:
        limit = int(limit)
    except ValueError:
        limit = 200
        
    sismos = database.get_sismos(filters=filters, limit=limit)
    return jsonify(sismos)

@app.route('/api/stats')
def api_stats():
    stats = database.get_stats()
    return jsonify(stats)

@app.route('/api/news')
def api_news():
    limit = request.args.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    news = database.get_news(limit=limit)
    return jsonify(news)

@app.route('/api/webcam/proxy')
def webcam_proxy():
    volcan = request.args.get('volcan', 'v_masaya')
    allowed_volcanoes = {
        'v_sancris2': 'https://webserver2.ineter.gob.ni/webcam/v_sancris2/image.jpg',
        'v_masaya': 'https://webserver2.ineter.gob.ni/webcam/v_masaya/image.jpg',
        'v_momotombo': 'https://webserver2.ineter.gob.ni/webcam/v_momotombo/image.jpg',
        'v_telica': 'https://webserver2.ineter.gob.ni/webcam/v_telica/image.jpg',
        'v_craterpoas': 'https://www.ovsicori.una.ac.cr/images/stories/camaras/livecraterpoas/camara.jpg',
        'v_chahuites': 'https://www.ovsicori.una.ac.cr/images/stories/camaras/livechahuites/camara.jpg',
        'v_curubande': 'https://www.ovsicori.una.ac.cr/images/stories/camaras/livecurubande/camara.jpg',
        'v_rincon2': 'https://www.ovsicori.una.ac.cr/images/stories/camaras/liverincon2/camara.jpg',
        'v_irazu': 'https://www.ovsicori.una.ac.cr/images/stories/camaras/liveirazu/camara.jpg',
        'v_concepcion2': 'https://webserver2.ineter.gob.ni/webcam/v_concepcion2/image.jpg',
        'v_concepcion3': 'https://webserver2.ineter.gob.ni/webcam/v_concepcion3/image.jpg',
        'v_masaya4': 'https://webserver2.ineter.gob.ni/webcam/v_masaya4/image.jpg',
        'v_turrialba': 'https://www.ovsicori.una.ac.cr/images/stories/camaras/liveturrialba/camara.jpg',
        'v_fuego_so': 'https://geo.insivumeh.gob.gt/fg8',
        'v_fuego_se': 'https://geo.insivumeh.gob.gt/fg12',
        'v_fuego_ceniza': 'https://geo.insivumeh.gob.gt/fg14',
        'v_santiaguito': 'https://geo.insivumeh.gob.gt/stpj'
    }
    
    if volcan not in allowed_volcanoes:
        return "Volcán no permitido o no registrado", 400
        
    url = allowed_volcanoes[volcan]
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            return Response(response.content, mimetype='image/jpeg')
        else:
            return f"Error de servidor de origen. Código: {response.status_code}", 502
    except Exception as e:
        return f"Error al conectar con la cámara: {e}", 502

@app.route('/api/seismogram')
def seismogram_proxy():
    date = request.args.get('date')       # Format: YYYYMMDD
    hour = request.args.get('hour')       # Format: HH (00 or 12)
    station = request.args.get('station') # Format: e.g., MASN, WILN
    
    if not date or not hour or not station:
        return "Parámetros insuficientes (requiere date, hour, station)", 400
        
    if '/' in station:
        parts = station.split('/', 1)
        folder = parts[0]
        prefix = parts[1]
    else:
        # Map station code to INETER directory and channel prefix
        station_mappings = {
            'WILN': {'folder': 'CRIN', 'prefix': 'CRIN_HHZ_NU_--'},
            'TELN': {'folder': 'TELN', 'prefix': 'HERN_EHZ_NU_00'},
            'CNGN': {'folder': 'CNGN', 'prefix': 'CNGA_EHZ_NU_00'},
            'MASN': {'folder': 'MASN', 'prefix': 'MASN_EHZ_NU_00'},
            'MOMN': {'folder': 'MOMN', 'prefix': 'MOM2_EHZ_NU_50'},
            'CONN': {'folder': 'CONN', 'prefix': 'ALTN_EHZ_NU_00'}
        }
        
        if station not in station_mappings:
            return "Estación sismológica no soportada", 400
            
        mapping = station_mappings[station]
        folder = mapping['folder']
        prefix = mapping['prefix']
        
    # Example URL: http://geofisica-ew1.ineter.gob.ni/sismogramas/MASN/MASN_EHZ_NU_00.2026052012.gif
    url = f"http://geofisica-ew1.ineter.gob.ni/sismogramas/{folder}/{prefix}.{date}{hour}.gif"
    
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            return Response(response.content, mimetype='image/gif')
        else:
            return f"Sismograma no encontrado en origen. Código: {response.status_code}", 404
    except Exception as e:
        return f"Error de conexión con INETER: {e}", 502

@app.route('/api/scrape/trigger', methods=['POST'])
def trigger_scrape():
    try:
        import scraper
        new_count = scraper.scrape_sismos()
        scraper.seed_initial_news()
        return jsonify({'success': True, 'new_sismos': new_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Running locally on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
