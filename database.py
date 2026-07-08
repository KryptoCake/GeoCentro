import sqlite3
import hashlib
import os
import math
import statistics
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geocentro.db')

# ============================================================================
# Constantes de Geoclasificación y Deduplicación
# Plan v4.1 — Decisiones D1–D9
# ============================================================================

# Bounding Boxes continentales para países de Centroamérica.
# El algoritmo clamp+Haversine resuelve ambigüedades en fronteras y zonas
# marítimas calculando la distancia mínima del epicentro a cada caja.
COUNTRY_BBOXES = {
    'Guatemala':   {'lat_min': 13.7, 'lat_max': 17.8, 'lon_min': -92.3, 'lon_max': -88.2},
    'El Salvador': {'lat_min': 13.1, 'lat_max': 14.5, 'lon_min': -90.1, 'lon_max': -87.7},
    'Honduras':    {'lat_min': 12.9, 'lat_max': 16.5, 'lon_min': -89.4, 'lon_max': -83.1},
    'Nicaragua':   {'lat_min': 10.7, 'lat_max': 15.0, 'lon_min': -87.7, 'lon_max': -83.0},
    'Costa Rica':  {'lat_min': 8.0,  'lat_max': 11.2, 'lon_min': -86.0, 'lon_max': -82.5},
    'Panamá':      {'lat_min': 7.2,  'lat_max': 9.7,  'lon_min': -83.0, 'lon_max': -77.2},
}

# Keywords para telesismos (sismos fuera de CA, >500 km del bbox más cercano)
TELESISMO_KEYWORDS = {
    'venezuela': 'Venezuela',
    'colombia': 'Colombia',
    'méxico': 'México', 'mexico': 'México',
    'ecuador': 'Ecuador',
    'guinea-bissau': 'Guinea-Bissau', 'guinea bissau': 'Guinea-Bissau',
    'perú': 'Perú', 'peru': 'Perú',
    'chile': 'Chile',
    'jamaica': 'Jamaica',
    'cuba': 'Cuba',
    'haití': 'Haití', 'haiti': 'Haití',
    'república dominicana': 'República Dominicana',
    'trinidad': 'Trinidad y Tobago',
    'estados unidos': 'Estados Unidos',
    'canada': 'Canadá', 'canadá': 'Canadá',
    'brazil': 'Brasil', 'brasil': 'Brasil',
}

# Jerarquía de agencias por país — D5: la dedup opera sobre 'agencia' (institución)
AGENCY_HIERARCHY = {
    'Costa Rica': ['OVSICORI', 'INETER'],
    'Nicaragua':  ['INETER', 'OVSICORI'],
}
DEFAULT_AGENCY_HIERARCHY = ['INETER', 'OVSICORI']

# Jerarquía de tipos de magnitud (MW es la preferida físicamente)
MAG_TYPE_PRIORITY = {'MW': 0, 'ML': 1, 'MC': 2}

# Ventana temporal de matching (D2: ±45 s)
MATCH_TIME_WINDOW = 45

# ============================================================================
# Funciones Utilitarias
# ============================================================================

def compute_t_epoch(fecha_utc, hora_utc):
    """Convierte fecha/hora UTC a epoch Unix. UTC EXPLÍCITO (D2).
    strptime produce datetime naive; .timestamp() sobre naive usa la zona
    LOCAL del sistema — bug latente si el VPS no corre en UTC.
    La forma correcta es .replace(tzinfo=timezone.utc)."""
    dt = datetime.strptime(f"{fecha_utc} {hora_utc}", "%Y-%m-%d %H:%M:%S")
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos geográficos (fórmula de Haversine)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def dist_to_bbox(lat, lon, bbox):
    """Distancia mínima (km) de un punto a un bounding box (D6).
    Usa clamping: proyecta el punto al borde más cercano de la caja.
    Si el punto está dentro del bbox, retorna 0."""
    clamp_lat = max(bbox['lat_min'], min(lat, bbox['lat_max']))
    clamp_lon = max(bbox['lon_min'], min(lon, bbox['lon_max']))
    if clamp_lat == lat and clamp_lon == lon:
        return 0.0
    return haversine(lat, lon, clamp_lat, clamp_lon)


def determinar_pais_coordenadas(lat, lon, descripcion=""):
    """Clasifica el país de un sismo basándose en coordenadas (dato duro)
    y descripción (solo para telesismos fuera de CA) — D6.

    Algoritmo:
    1. Distancia mínima al bounding box de cada país de CA
    2. País con distancia mínima gana si d <= 500 km
    3. Si d > 500 km: keywords en descripción para países lejanos
    4. Sin match → 'Otros'
    """
    min_dist = float('inf')
    closest_country = 'Otros'

    for country, bbox in COUNTRY_BBOXES.items():
        d = dist_to_bbox(lat, lon, bbox)
        if d < min_dist:
            min_dist = d
            closest_country = country

    if min_dist <= 500.0:
        return closest_country

    # Telesismo: buscar keywords en la descripción
    desc_lower = (descripcion or "").lower()
    for keyword, country_name in TELESISMO_KEYWORDS.items():
        if keyword in desc_lower:
            return country_name

    return 'Otros'


def get_agency_from_tipo(tipo):
    """Deriva agencia y feed a partir del campo 'tipo' de la BD histórica.
    Usado solo para migración de datos existentes (§5 del plan)."""
    tipo_upper = (tipo or '').upper().strip()
    if tipo_upper == 'CR_REC':
        return 'OVSICORI', 'OVSICORI_REC'
    elif tipo_upper == 'CR_SEN':
        return 'OVSICORI', 'OVSICORI_SEN'
    elif tipo_upper in ('C', 'MW', 'ML', 'MC', 'A'):
        return 'INETER', 'INETER'
    else:
        return 'INETER', 'HISTORICO'


# ============================================================================
# Conexión y Inicialización de Base de Datos
# ============================================================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # D7: WAL + busy_timeout para concurrencia segura
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create sismos table (canónica — deduplicada)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sismos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_utc TEXT NOT NULL,
            hora_utc TEXT NOT NULL,
            latitud REAL NOT NULL,
            longitud REAL NOT NULL,
            profundidad INTEGER NOT NULL,
            magnitud REAL NOT NULL,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            pais TEXT NOT NULL,
            hash_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migración: agregar t_epoch a sismos si no existe
    cursor.execute("PRAGMA table_info(sismos)")
    sismos_columns = [row[1] for row in cursor.fetchall()]
    if 't_epoch' not in sismos_columns:
        cursor.execute("ALTER TABLE sismos ADD COLUMN t_epoch INTEGER")

    # Índice sobre t_epoch en sismos (para matching de deduplicación)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sismos_tepoch ON sismos(t_epoch)")

    # Create sismos_raw table (capa cruda — todo reporte, nunca se borra) — D1
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sismos_raw (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_utc           TEXT NOT NULL,
            hora_utc            TEXT NOT NULL,
            t_epoch             INTEGER NOT NULL,
            latitud             REAL NOT NULL,
            longitud            REAL NOT NULL,
            profundidad         REAL,
            magnitud            REAL NOT NULL,
            tipo                TEXT,
            descripcion         TEXT,
            pais                TEXT,
            hash_id             TEXT,
            agencia             TEXT NOT NULL,
            feed                TEXT NOT NULL,
            scraped_at          INTEGER NOT NULL,
            sismo_canonical_id  INTEGER REFERENCES sismos(id),
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_tepoch ON sismos_raw(t_epoch)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_canonical ON sismos_raw(sismo_canonical_id)")

    # Create news table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            url TEXT NOT NULL,
            fecha TEXT NOT NULL,
            resumen TEXT,
            pais TEXT NOT NULL,
            categoria TEXT DEFAULT 'general',
            hash_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Run migration to add columns to 'news' table if they do not exist
    cursor.execute("PRAGMA table_info(news)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'categoria' not in columns:
        cursor.execute("ALTER TABLE news ADD COLUMN categoria TEXT DEFAULT 'general'")
    if 'imagen_url' not in columns:
        cursor.execute("ALTER TABLE news ADD COLUMN imagen_url TEXT")

    # Clean up old weather alerts that have invalid, empty, or relative URLs
    cursor.execute("DELETE FROM news WHERE categoria = 'clima' AND (url IS NULL OR url = '' OR url = '#' OR url LIKE '#%' OR url NOT LIKE 'http%')")

    # Create sismos_usgs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sismos_usgs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usgs_id TEXT UNIQUE NOT NULL,
            fecha_utc TEXT NOT NULL,
            hora_utc TEXT NOT NULL,
            latitud REAL NOT NULL,
            longitud REAL NOT NULL,
            profundidad REAL NOT NULL,
            magnitud REAL NOT NULL,
            tipo_magnitud TEXT,
            descripcion TEXT NOT NULL,
            pais TEXT NOT NULL,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ============================================================================
# Funciones de Hash
# ============================================================================

def generate_sismo_hash(fecha_utc, hora_utc, latitud, longitud):
    # Standardize formats and coordinates to avoid rounding mismatches
    data = f"{fecha_utc.strip()}|{hora_utc.strip()}|{float(latitud):.4f}|{float(longitud):.4f}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_news_hash(titulo, url):
    data = f"{titulo.strip()}|{url.strip()}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


# ============================================================================
# Operaciones Core de Sismos — Deduplicación (D1–D9)
# ============================================================================

def save_sismo(fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo,
               descripcion, agencia, feed, scraped_at):
    """Inserta un reporte en sismos_raw y ejecuta deduplicación en caliente.
    Transparente para el resto del código: la UI sigue leyendo 'sismos'.
    Retorna True si el reporte fue insertado (nuevo en raw), False si ya existía."""
    hash_id = generate_sismo_hash(fecha_utc, hora_utc, latitud, longitud)
    t_epoch = compute_t_epoch(fecha_utc, hora_utc)
    pais = determinar_pais_coordenadas(latitud, longitud, descripcion)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    # Manual transaction control para BEGIN IMMEDIATE (D7)
    conn.isolation_level = None

    try:
        conn.execute("BEGIN IMMEDIATE")

        # Check if this exact report already exists in raw (mismo hash = misma fuente, mismo evento)
        existing = conn.execute(
            "SELECT id FROM sismos_raw WHERE hash_id = ?", (hash_id,)
        ).fetchone()
        if existing:
            conn.execute("COMMIT")
            return False

        # Insert into sismos_raw
        cursor = conn.execute('''
            INSERT INTO sismos_raw (fecha_utc, hora_utc, t_epoch, latitud, longitud,
                                    profundidad, magnitud, tipo, descripcion, pais,
                                    hash_id, agencia, feed, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha_utc, hora_utc, t_epoch, latitud, longitud, profundidad,
              magnitud, tipo, descripcion, pais, hash_id, agencia, feed, scraped_at))
        raw_id = cursor.lastrowid

        # Deduplicate within the same transaction
        _deduplicate_and_sync(conn, raw_id)

        conn.execute("COMMIT")
        return True
    except sqlite3.IntegrityError:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        return False
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _deduplicate_and_sync(conn, raw_id):
    """Deduplicación en caliente — §2.3 del plan.
    DEBE ejecutarse dentro de una transacción BEGIN IMMEDIATE ya abierta.

    Busca candidatos en sismos (canónica) dentro de ±45 s y distancia adaptativa.
    Si encuentra match: asocia y recalcula el canónico.
    Si no: crea nuevo canónico con id = raw.id (D8: ids inmutables)."""
    raw = conn.execute("SELECT * FROM sismos_raw WHERE id = ?", (raw_id,)).fetchone()
    if not raw:
        return

    # Buscar candidatos en la tabla canónica dentro de la ventana temporal (D2)
    candidates = conn.execute(
        "SELECT * FROM sismos WHERE t_epoch BETWEEN ? AND ?",
        (raw['t_epoch'] - MATCH_TIME_WINDOW, raw['t_epoch'] + MATCH_TIME_WINDOW)
    ).fetchall()

    match = None
    best_score = float('inf')

    for c in candidates:
        # D3: distancia adaptativa continua
        max_mag = max(raw['magnitud'], c['magnitud'])
        dist_limit = max(60.0, min(60.0 + 40.0 * (max_mag - 4.0), 250.0))
        d = haversine(raw['latitud'], raw['longitud'], c['latitud'], c['longitud'])

        if d <= dist_limit:
            # Score determinista: normaliza ambos términos a [0,1] (D9)
            score = d / dist_limit + abs(raw['t_epoch'] - c['t_epoch']) / float(MATCH_TIME_WINDOW)
            if score < best_score:
                match = c
                best_score = score

    if match is None:
        # Nuevo evento canónico — heredar id del raw fundador (D8)
        pais = determinar_pais_coordenadas(raw['latitud'], raw['longitud'], raw['descripcion'])
        conn.execute('''
            INSERT INTO sismos (id, fecha_utc, hora_utc, latitud, longitud, profundidad,
                               magnitud, tipo, descripcion, pais, hash_id, t_epoch)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (raw_id, raw['fecha_utc'], raw['hora_utc'], raw['latitud'], raw['longitud'],
              raw['profundidad'], raw['magnitud'], raw['tipo'], raw['descripcion'],
              pais, raw['hash_id'], raw['t_epoch']))
        canonical_id = raw_id
    else:
        canonical_id = match['id']

    # Asociar el reporte raw al canónico
    conn.execute(
        "UPDATE sismos_raw SET sismo_canonical_id = ? WHERE id = ?",
        (canonical_id, raw_id)
    )

    # Recalcular el canónico si hubo match (actualización por nueva info)
    if match is not None:
        _recalcular_canonico(conn, canonical_id)


def _recalcular_canonico(conn, canonical_id):
    """Recalcula los datos del evento canónico a partir de sus reportes raw — §2.4.
    DEBE ejecutarse dentro de una transacción ya abierta.

    1. Un solo reporte por INSTITUCIÓN (no por feed) — D4, D5
    2. Magnitud canónica = mediana de esos reportes filtrados
    3. Representativo elegido por jerarquía de agencia + tipo de magnitud"""
    raw_reports = conn.execute(
        "SELECT * FROM sismos_raw WHERE sismo_canonical_id = ?",
        (canonical_id,)
    ).fetchall()

    if not raw_reports:
        return

    # Filtrar: un reporte por institución (agencia), el más reciente (D9)
    by_agency = {}
    for r in raw_reports:
        ag = r['agencia']
        if ag not in by_agency:
            by_agency[ag] = r
        else:
            existing = by_agency[ag]
            # ORDER BY scraped_at DESC, id DESC (D9: desempate determinista)
            if (r['scraped_at'] > existing['scraped_at'] or
                    (r['scraped_at'] == existing['scraped_at'] and r['id'] > existing['id'])):
                by_agency[ag] = r

    filtered = list(by_agency.values())

    # D4: magnitud canónica = mediana de un reporte por institución, 1 decimal
    magnitudes = [r['magnitud'] for r in filtered]
    mag_canonica = round(statistics.median(magnitudes), 1)

    # Determinar país provisional para seleccionar jerarquía de agencia
    sample = filtered[0]
    pais_provisional = determinar_pais_coordenadas(
        sample['latitud'], sample['longitud'], sample['descripcion']
    )

    # Jerarquía de agencia por país del evento
    hierarchy = AGENCY_HIERARCHY.get(pais_provisional, DEFAULT_AGENCY_HIERARCHY)

    # Seleccionar representativo (D9: desempates deterministas en todo)
    def sort_key(r):
        ag_rank = hierarchy.index(r['agencia']) if r['agencia'] in hierarchy else len(hierarchy)
        tipo_upper = (r['tipo'] or '').upper()
        mag_rank = MAG_TYPE_PRIORITY.get(tipo_upper, 99)
        return (ag_rank, mag_rank, -r['scraped_at'], -r['id'])

    filtered.sort(key=sort_key)
    rep = filtered[0]

    # País definitivo desde las coordenadas del representativo (D6)
    pais_rep = determinar_pais_coordenadas(rep['latitud'], rep['longitud'], rep['descripcion'])

    # Actualizar canónico (el id NUNCA cambia — D8: inmutable)
    conn.execute('''
        UPDATE sismos SET
            fecha_utc = ?, hora_utc = ?, latitud = ?, longitud = ?,
            profundidad = ?, magnitud = ?, tipo = ?, descripcion = ?,
            pais = ?, t_epoch = ?
        WHERE id = ?
    ''', (rep['fecha_utc'], rep['hora_utc'], rep['latitud'], rep['longitud'],
          rep['profundidad'], mag_canonica, rep['tipo'], rep['descripcion'],
          pais_rep, rep['t_epoch'], canonical_id))


# ============================================================================
# Consultas de Sismos
# ============================================================================

def get_sismo_by_id(sismo_id):
    """Busca un sismo por ID con rescate transparente de IDs duplicados — §2.5.
    Si el ID no existe en sismos (canónica), busca en sismos_raw y redirige
    al canónico asociado. Ningún enlace histórico muere."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Intento directo en canónica
    cursor.execute("SELECT * FROM sismos WHERE id = ?", (sismo_id,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return dict(row)

    # Rescate: buscar en raw y redirigir al canónico
    cursor.execute(
        "SELECT sismo_canonical_id FROM sismos_raw WHERE id = ? AND sismo_canonical_id IS NOT NULL",
        (sismo_id,)
    )
    raw = cursor.fetchone()
    if raw:
        cursor.execute("SELECT * FROM sismos WHERE id = ?", (raw['sismo_canonical_id'],))
        canonical = cursor.fetchone()
        conn.close()
        return dict(canonical) if canonical else None

    conn.close()
    return None


def get_sismos(filters=None, limit=200):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM sismos"
    params = []

    if filters:
        where_clauses = []
        if 'pais' in filters and filters['pais']:
            where_clauses.append("pais = ?")
            params.append(filters['pais'])
        if 'min_magnitud' in filters and filters['min_magnitud'] is not None:
            where_clauses.append("magnitud >= ?")
            params.append(float(filters['min_magnitud']))
        if 'max_magnitud' in filters and filters['max_magnitud'] is not None:
            where_clauses.append("magnitud <= ?")
            params.append(float(filters['max_magnitud']))
        if 'profundidad_min' in filters and filters['profundidad_min'] is not None:
            where_clauses.append("profundidad >= ?")
            params.append(int(filters['profundidad_min']))
        if 'profundidad_max' in filters and filters['profundidad_max'] is not None:
            where_clauses.append("profundidad <= ?")
            params.append(int(filters['profundidad_max']))
        if 'fecha_inicio' in filters and filters['fecha_inicio']:
            where_clauses.append("fecha_utc >= ?")
            params.append(filters['fecha_inicio'])
        if 'fecha_fin' in filters and filters['fecha_fin']:
            where_clauses.append("fecha_utc <= ?")
            params.append(filters['fecha_fin'])
        if 'buscar' in filters and filters['buscar']:
            where_clauses.append("descripcion LIKE ?")
            params.append(f"%{filters['buscar']}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY fecha_utc DESC, hora_utc DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_news(limit=10, categoria=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if categoria:
        cursor.execute("SELECT * FROM news WHERE categoria = ? ORDER BY fecha DESC, created_at DESC LIMIT ?", (categoria, limit))
    else:
        cursor.execute("SELECT * FROM news ORDER BY fecha DESC, created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}

    # Total count
    cursor.execute("SELECT COUNT(*) FROM sismos")
    stats['total_sismos'] = cursor.fetchone()[0]

    if stats['total_sismos'] == 0:
        conn.close()
        return {
            'total_sismos': 0,
            'max_magnitud': 0,
            'avg_profundidad': 0,
            'por_pais': {},
            'por_magnitud': {'bajo': 0, 'moderado': 0, 'fuerte': 0},
            'sismos_por_dia': []
        }

    # Max magnitude
    cursor.execute("SELECT MAX(magnitud) FROM sismos")
    val_max = cursor.fetchone()[0]
    stats['max_magnitud'] = float(val_max) if val_max is not None else 0.0

    # Avg depth
    cursor.execute("SELECT AVG(profundidad) FROM sismos")
    val_avg = cursor.fetchone()[0]
    stats['avg_profundidad'] = round(float(val_avg), 1) if val_avg is not None else 0.0

    # Sismos by country
    cursor.execute("SELECT pais, COUNT(*) as cantidad FROM sismos GROUP BY pais ORDER BY cantidad DESC")
    stats['por_pais'] = {row['pais']: row['cantidad'] for row in cursor.fetchall()}

    # Sismos by magnitude range
    cursor.execute("""
        SELECT
            SUM(CASE WHEN magnitud < 3.0 THEN 1 ELSE 0 END) as bajo,
            SUM(CASE WHEN magnitud >= 3.0 AND magnitud < 5.0 THEN 1 ELSE 0 END) as moderado,
            SUM(CASE WHEN magnitud >= 5.0 THEN 1 ELSE 0 END) as fuerte
        FROM sismos
    """)
    row = cursor.fetchone()
    stats['por_magnitud'] = {
        'bajo': row[0] or 0,
        'moderado': row[1] or 0,
        'fuerte': row[2] or 0
    }

    # Daily counts for chart (last 10 days with activity)
    cursor.execute("""
        SELECT fecha_utc, COUNT(*) as cantidad
        FROM sismos
        GROUP BY fecha_utc
        ORDER BY fecha_utc DESC
        LIMIT 10
    """)
    stats['sismos_por_dia'] = [{'fecha': row[0], 'cantidad': row[1]} for row in cursor.fetchall()][::-1]

    conn.close()
    return stats


# ============================================================================
# Funciones de Noticias
# ============================================================================

def save_news(titulo, url, fecha, resumen, pais, categoria='general', imagen_url=None):
    hash_id = generate_news_hash(titulo, url)
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = False
    try:
        cursor.execute('''
            INSERT INTO news (titulo, url, fecha, resumen, pais, categoria, imagen_url, hash_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (titulo, url, fecha, resumen, pais, categoria, imagen_url, hash_id))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        inserted = False
    finally:
        conn.close()
    return inserted

def update_news(news_id, titulo=None, url=None, fecha=None, resumen=None, pais=None, categoria=None, imagen_url=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if titulo is not None:
        updates.append("titulo = ?")
        params.append(titulo)
    if url is not None:
        updates.append("url = ?")
        params.append(url)
    if fecha is not None:
        updates.append("fecha = ?")
        params.append(fecha)
    if resumen is not None:
        updates.append("resumen = ?")
        params.append(resumen)
    if pais is not None:
        updates.append("pais = ?")
        params.append(pais)
    if categoria is not None:
        updates.append("categoria = ?")
        params.append(categoria)
    if imagen_url is not None:
        updates.append("imagen_url = ?")
        params.append(imagen_url)

    if not updates:
        conn.close()
        return False

    # If title or url is updated, we recompute hash_id to keep it consistent
    if titulo is not None or url is not None:
        cursor.execute("SELECT titulo, url FROM news WHERE id = ?", (news_id,))
        row = cursor.fetchone()
        if row:
            current_title = titulo if titulo is not None else row['titulo']
            current_url = url if url is not None else row['url']
            new_hash = generate_news_hash(current_title, current_url)
            updates.append("hash_id = ?")
            params.append(new_hash)

    params.append(news_id)
    query = f"UPDATE news SET {', '.join(updates)} WHERE id = ?"

    success = False
    try:
        cursor.execute(query, params)
        conn.commit()
        success = cursor.rowcount > 0
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def delete_news(news_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    success = False
    try:
        cursor.execute("DELETE FROM news WHERE id = ?", (news_id,))
        conn.commit()
        success = cursor.rowcount > 0
    finally:
        conn.close()
    return success

def get_news_by_id(news_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news WHERE id = ?", (news_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================================
# Funciones USGS (tabla separada — no afectada por deduplicación)
# ============================================================================

def save_sismo_usgs(usgs_id, fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo_magnitud, descripcion, pais, url):
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = False
    try:
        cursor.execute('''
            INSERT INTO sismos_usgs (usgs_id, fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo_magnitud, descripcion, pais, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (usgs_id, fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo_magnitud, descripcion, pais, url))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        inserted = False
    finally:
        conn.close()
    return inserted

def get_sismos_usgs(filters=None, limit=200):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM sismos_usgs"
    params = []

    if filters:
        where_clauses = []
        if 'pais' in filters and filters['pais']:
            if filters['pais'] == 'Otros':
                where_clauses.append("pais NOT IN ('Nicaragua', 'El Salvador', 'Guatemala', 'Honduras', 'Costa Rica')")
            else:
                where_clauses.append("pais = ?")
                params.append(filters['pais'])
        if 'min_magnitud' in filters and filters['min_magnitud'] is not None:
            where_clauses.append("magnitud >= ?")
            params.append(float(filters['min_magnitud']))
        if 'max_magnitud' in filters and filters['max_magnitud'] is not None:
            where_clauses.append("magnitud <= ?")
            params.append(float(filters['max_magnitud']))
        if 'profundidad_min' in filters and filters['profundidad_min'] is not None:
            where_clauses.append("profundidad >= ?")
            params.append(int(filters['profundidad_min']))
        if 'profundidad_max' in filters and filters['profundidad_max'] is not None:
            where_clauses.append("profundidad <= ?")
            params.append(int(filters['profundidad_max']))
        if 'fecha_inicio' in filters and filters['fecha_inicio']:
            where_clauses.append("fecha_utc >= ?")
            params.append(filters['fecha_inicio'])
        if 'fecha_fin' in filters and filters['fecha_fin']:
            where_clauses.append("fecha_utc <= ?")
            params.append(filters['fecha_fin'])
        if 'buscar' in filters and filters['buscar']:
            where_clauses.append("descripcion LIKE ?")
            params.append(f"%{filters['buscar']}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY fecha_utc DESC, hora_utc DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
