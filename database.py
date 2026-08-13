import sqlite3
import hashlib
import os
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from shapely.geometry import Polygon, Point

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

# Países de Centroamérica detectables en la descripción del sismo.
# INETER/OVSICORI siempre cierran la descripción con el país de referencia
# ("... Km al sur de Playa El Cuco, El Salvador"), por lo que la descripción es
# la fuente más fiable para clasificar el país — sobre todo en epicentros
# mar adentro cerca de fronteras, donde la distancia al bounding box fallaba.
CA_DESC_KEYWORDS = {
    'costa rica': 'Costa Rica',
    'el salvador': 'El Salvador',
    'guatemala': 'Guatemala',
    'honduras': 'Honduras',
    'nicaragua': 'Nicaragua',
    'panamá': 'Panamá',
    'panama': 'Panamá',
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
# Lista negra de sismos fantasma (reportes erróneos de agencias ya corregidos)
# ----------------------------------------------------------------------------
# Caso 2026-08-10: OVSICORI publicó una localización preliminar errónea del
# M7.4 de Colombia como "M6.6, 58.3 km al Sur de Panama" (06:35:40, 7.6121,
# -80.9196). El evento real NO existe: USGS no lo registra y OVSICORI luego lo
# corrigió a Colombia (M7.5, 06:34:29). Mientras OVSICORI no retire la fila de
# su feed, el scraper reintentaría reinsertarla cada 30 min; este bloqueo lo
# impide. El hash = sha256(fecha|hora|lat.4|lon.4), ver generate_sismo_hash.
# ============================================================================
HASHES_BLOQUEADOS = {
    # Hash calculado con la hora local original (06:35:40) — el bug pre-fix
    'fac7173653d47e655d3057cd7db5d82fd241447ac45b8d27acf9c37ba70d5905',
    # Hash calculado con la hora UTC real (12:35:40) — el scraper corregido lo genera así
    'b4f1ae311836b2686b5f9e032b45cb1bbc03bc1ca15e7f94b97fd09712b2ab04',
}

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


def _pais_desde_descripcion(desc_lower):
    """Devuelve el país nombrado en la descripción, o None si no hay match.

    Usa coincidencia de palabra completa (word boundary) para evitar falsos
    positivos por subcadenas: p.ej. 'Brasilito' (playa de Guanacaste) no debe
    casar con 'brasil', ni 'Los Chiles' (Alajuela) con 'chile'.
    """
    for keyword, country_name in CA_DESC_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', desc_lower):
            return country_name
    for keyword, country_name in TELESISMO_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', desc_lower):
            return country_name
    return None


def determinar_pais_coordenadas(lat, lon, descripcion=""):
    """Clasifica el país de un sismo — D6 (revisado 2026-08-13).

    Prioridad:
    1. País nombrado en la descripción (INETER/OVSICORI lo indican de forma
       explícita: "... Km al sur de Playa El Cuco, El Salvador"). Es la fuente
       más fiable, sobre todo para epicentros mar adentro cerca de fronteras,
       donde la distancia al bounding box fallaba (asignaba Honduras a un sismo
       frente a El Salvador, o Guatemala a un sismo de México).
    2. Si la descripción no nombra un país: distancia mínima al bounding box de
       cada país de CA (gana el más cercano si d <= 500 km).
    3. Sin match → 'Otros'.
    """
    desc_lower = (descripcion or "").lower()

    # 1-2. País nombrado explícitamente en la descripción (CA primero, luego telesismos)
    pais_desc = _pais_desde_descripcion(desc_lower)
    if pais_desc:
        return pais_desc

    # 3. Fallback por coordenadas: país de CA más cercano (si d <= 500 km)
    min_dist = float('inf')
    closest_country = 'Otros'

    for country, bbox in COUNTRY_BBOXES.items():
        d = dist_to_bbox(lat, lon, bbox)
        if d < min_dist:
            min_dist = d
            closest_country = country

    if min_dist <= 500.0:
        return closest_country

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

    # Create poligonos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poligonos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            peso REAL,
            unidad TEXT,
            color TEXT DEFAULT '#ff5722',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create poligono_puntos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poligono_puntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poligono_id INTEGER NOT NULL REFERENCES poligonos(id) ON DELETE CASCADE,
            latitud REAL NOT NULL,
            longitud REAL NOT NULL,
            orden INTEGER NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_puntos_poligono ON poligono_puntos(poligono_id)")

    # Precargar polígonos por defecto
    _precargar_poligonos_defecto(conn)

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
    if hash_id in HASHES_BLOQUEADOS:
        print(f"[BLOQUEADO] sismo fantasma ignorado (hash en lista negra): "
              f"{fecha_utc} {hora_utc} M{magnitud} {descripcion}")
        return False
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


# ============================================================================
# Módulo de Riesgo Sísmico y Polígonos de Interoperabilidad KML
# ============================================================================

def _precargar_poligonos_defecto(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM poligonos")
    if cursor.fetchone()[0] > 0:
        return # Ya hay datos
    
    # Precargar 3 polígonos representativos de Centroamérica (Nicaragua)
    poligonos_demo = [
        {
            "nombre": "Área Metropolitana de Managua (Fallas locales)",
            "descripcion": "Zona urbana de Managua propensa a sismos corticales por fallamiento local. Incluye fallas activas como Tiscapa, Estadio y Chico Largo.",
            "peso": 1500000.0,
            "unidad": "Habitantes expuestos",
            "color": "#f44336",
            "puntos": [
                (12.1600, -86.3200),
                (12.1600, -86.2000),
                (12.0800, -86.2000),
                (12.0800, -86.3200),
                (12.1600, -86.3200) # Cerrado
            ]
        },
        {
            "nombre": "León - Chinandega (Región de Suelos Blandos)",
            "descripcion": "Zona costera y de planicie del noroeste caracterizada por suelos arcillosos y volcánicos que amplifican las ondas de subducción.",
            "peso": 420000.0,
            "unidad": "Habitantes expuestos",
            "color": "#ff9800",
            "puntos": [
                (12.6000, -87.1000),
                (12.6000, -86.7000),
                (12.3000, -86.7000),
                (12.3000, -87.1000),
                (12.6000, -87.1000) # Cerrado
            ]
        },
        {
            "nombre": "Zona de Influencia Activa - Complejo Volcánico Masaya",
            "descripcion": "Área con alta susceptibilidad a enjambres sísmicos volcánicos y deformación de terreno asociada al lago de lava activo.",
            "peso": 30000.0,
            "unidad": "Habitantes expuestos",
            "color": "#e91e63",
            "puntos": [
                (12.0200, -86.1500),
                (12.0200, -86.0500),
                (11.9500, -86.0500),
                (11.9500, -86.1500),
                (12.0200, -86.1500) # Cerrado
            ]
        }
    ]

    for p in poligonos_demo:
        try:
            cursor.execute('''
                INSERT INTO poligonos (nombre, descripcion, peso, unidad, color)
                VALUES (?, ?, ?, ?, ?)
            ''', (p["nombre"], p["descripcion"], p["peso"], p["unidad"], p["color"]))
            poligono_id = cursor.lastrowid
            
            for i, pt in enumerate(p["puntos"]):
                cursor.execute('''
                    INSERT INTO poligono_puntos (poligono_id, latitud, longitud, orden)
                    VALUES (?, ?, ?, ?)
                ''', (poligono_id, pt[0], pt[1], i))
        except Exception as e:
            print(f"Error al precargar polígono: {e}")


def add_poligono(nombre, descripcion, peso, unidad, puntos, color=None):
    """Agrega un polígono y sus puntos (vértices) de forma transaccional.
    puntos es una lista de tuplas o diccionarios con (lat, lon)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    success = False
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute('''
            INSERT INTO poligonos (nombre, descripcion, peso, unidad, color)
            VALUES (?, ?, ?, ?, ?)
        ''', (nombre, descripcion, peso, unidad, color or '#ff5722'))
        poligono_id = cursor.lastrowid
        
        for i, pt in enumerate(puntos):
            lat = pt[0] if isinstance(pt, (tuple, list)) else pt.get('lat')
            lon = pt[1] if isinstance(pt, (tuple, list)) else pt.get('lon')
            cursor.execute('''
                INSERT INTO poligono_puntos (poligono_id, latitud, longitud, orden)
                VALUES (?, ?, ?, ?)
            ''', (poligono_id, lat, lon, i))
        
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        print(f"Error al insertar polígono: {e}")
        success = False
    finally:
        conn.close()
    return success


def get_poligonos():
    """Retorna todos los polígonos con sus vértices estructurados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM poligonos ORDER BY id")
    polys = cursor.fetchall()
    
    result = []
    for poly in polys:
        poly_dict = dict(poly)
        cursor.execute("SELECT latitud, longitud, orden FROM poligono_puntos WHERE poligono_id = ? ORDER BY orden", (poly_dict['id'],))
        pts = cursor.fetchall()
        poly_dict['puntos'] = [{'lat': p['latitud'], 'lon': p['longitud']} for p in pts]
        result.append(poly_dict)
        
    conn.close()
    return result


_GRID_CACHE = None

def _cargar_cache_grilla():
    global _GRID_CACHE
    if _GRID_CACHE is not None:
        return _GRID_CACHE
    
    ruta_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Prob_calc', 'datos', 'celdas_atributos.csv')
    if not os.path.exists(ruta_csv):
        return None
        
    try:
        # Importación diferida para no penalizar el arranque global
        import pandas as pd
        df = pd.read_csv(ruta_csv)
        # Convertir a un diccionario rápido indexado por 'idx'
        _GRID_CACHE = {row['idx']: row for row in df.to_dict(orient='records')}
    except Exception as e:
        print(f"Error al cargar grilla en memoria: {e}")
        _GRID_CACHE = None
    return _GRID_CACHE


def evaluar_punto(lat, lon):
    """Evalúa la pertenencia a polígonos (Shapely) y los parámetros geofísicos (Vs30/Slab2)."""
    # 1. Evaluar polígonos relacionales (Shapely)
    poligonos = get_poligonos()
    poligonos_activos = []
    
    point = Point(lon, lat) # Shapely usa (longitud, latitud)
    for p in poligonos:
        if len(p['puntos']) >= 3:
            coords = [(pt['lon'], pt['lat']) for pt in p['puntos']]
            try:
                poly = Polygon(coords)
                if poly.contains(point):
                    poligonos_activos.append({
                        'nombre': p['nombre'],
                        'descripcion': p['descripcion'],
                        'peso': p['peso'],
                        'unidad': p['unidad'],
                        'color': p['color']
                    })
            except Exception as e:
                print(f"Error al evaluar geometría de polígono {p['nombre']}: {e}")
                
    # 2. Consultar grilla de Prob_calc
    grilla = _cargar_cache_grilla()
    vs30 = None
    clase_sitio = "?"
    amp_factor = 0.0
    slab_prof = None
    en_grilla = False
    
    # Importación diferida de config_grilla
    try:
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Prob_calc'))
        import config_grilla as CG
        idx = int(CG.indice_celda(lat, lon))
        if idx != -1 and grilla is not None and idx in grilla:
            celda_data = grilla[idx]
            # Las celdas fuera de cobertura traen NaN (p.ej. slab_prof_km fuera
            # de la zona de subducción); NaN no es JSON válido y rompe el fetch
            # del navegador, así que se normaliza a None/valores neutros.
            def _num(v, default=None):
                try:
                    f = float(v)
                except (TypeError, ValueError):
                    return default
                return default if math.isnan(f) else f

            vs30 = _num(celda_data.get('vs30_ms'))
            clase = celda_data.get('clase_sitio')
            clase_sitio = clase if isinstance(clase, str) else '?'
            amp_factor = _num(celda_data.get('amp_factor'), 0.0)
            slab_prof = _num(celda_data.get('slab_prof_km'))
            en_grilla = True
    except Exception as e:
        print(f"Error al consultar grilla Prob_calc: {e}")
        
    # 3. Calcular heurística de riesgo científica
    # Amenaza base
    hazard = 40.0
    
    # Si está en el arco volcánico / pacífico
    if lon < -85.5:
        # Ecuación de distancia de Fable 5
        dist_volc = abs(lat - (-0.73 * lon - 51.1)) / math.sqrt(1 + 0.73**2)
        hazard = 85.0 - (dist_volc * 15.0)
        if hazard < 55.0:
            hazard = 55.0
        
        # Managua fault system
        dist_mng = math.sqrt((lat - 12.13)**2 + (lon - -86.25)**2)
        if dist_mng < 0.4:
            hazard += (0.4 - dist_mng) * 35.0
    else:
        hazard = 55.0
        
    # Factor por polígonos activos (acumulativo)
    # Por ejemplo, si está en el complejo Masaya o Managua fallas, incrementamos la amenaza
    incremento_polys = 0.0
    for pa in poligonos_activos:
        if "falla" in pa['nombre'].lower() or "volcán" in pa['nombre'].lower() or "activo" in pa['nombre'].lower():
            incremento_polys += 15.0
            
    hazard += incremento_polys
    hazard = min(95.0, max(20.0, hazard))
    
    # Vulnerabilidad y Efecto de sitio (Vs30)
    # Si tenemos Vs30 real, lo incorporamos
    efecto_sitio_mult = 1.0
    if en_grilla and vs30 is not None:
        # A mayor Vs30 (roca), menor amplificación. A menor Vs30 (barro), mayor.
        # amp_factor oscila habitualmente entre -1.0 y 1.5. Lo normalizamos para el score de riesgo
        efecto_sitio_mult = 1.0 + (amp_factor * 0.4)
        
    # Score combinado final de base (asumiendo estructura moderada por defecto 0.5)
    # Para la calculadora interactiva general del mapa
    score = round(hazard * (0.3 + 0.7 * (0.5 * efecto_sitio_mult)))
    score = min(100, max(1, score))
    
    return {
        'lat': lat,
        'lon': lon,
        'score': score,
        'en_grilla': en_grilla,
        'vs30': vs30,
        'clase_sitio': clase_sitio,
        'amp_factor': amp_factor,
        'slab_prof_km': slab_prof,
        'poligonos': poligonos_activos
    }


def generar_kml():
    """Genera un archivo XML en el estándar oficial de KML de todos los polígonos."""
    poligonos = get_poligonos()
    kml = []
    kml.append('<?xml version="1.0" encoding="UTF-8"?>')
    kml.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    kml.append('<Document>')
    kml.append('  <name>Polígonos de Riesgo GeoCentro</name>')
    kml.append('  <description>Capa de polígonos de riesgo sísmico y exposición</description>')
    
    for p in poligonos:
        # KML color: aabbggrr -> convert from hex #rrggbb
        # Si p['color'] es #ff5722 (rojo), en KML con opacidad 40% (64):
        # 64 + 22 (azul/b) + 57 (verde/g) + ff (rojo/r) -> 642257ff
        hex_col = p["color"].replace("#", "")
        if len(hex_col) == 6:
            r = hex_col[0:2]
            g = hex_col[2:4]
            b = hex_col[4:6]
            kml_line_color = f"ff{b}{g}{r}"
            kml_poly_color = f"64{b}{g}{r}" # 40% opacidad
        else:
            kml_line_color = "ff2257ff"
            kml_poly_color = "642257ff"

        kml.append('  <Placemark>')
        kml.append(f'    <name>{p["nombre"]}</name>')
        kml.append(f'    <description>{p["descripcion"]}</description>')
        kml.append('    <Style>')
        kml.append('      <LineStyle>')
        kml.append(f'        <color>{kml_line_color}</color>')
        kml.append('        <width>2</width>')
        kml.append('      </LineStyle>')
        kml.append('      <PolyStyle>')
        kml.append(f'        <color>{kml_poly_color}</color>')
        kml.append('      </PolyStyle>')
        kml.append('    </Style>')
        kml.append('    <ExtendedData>')
        kml.append(f'      <Data name="peso"><value>{p["peso"]}</value></Data>')
        kml.append(f'      <Data name="unidad"><value>{p["unidad"]}</value></Data>')
        kml.append('    </ExtendedData>')
        kml.append('    <Polygon>')
        kml.append('      <outerBoundaryIs>')
        kml.append('        <LinearRing>')
        kml.append('          <coordinates>')
        
        coord_strings = []
        for pt in p['puntos']:
            coord_strings.append(f"{pt['lon']},{pt['lat']},0")
        
        # Cerrar el polígono si no está cerrado
        if p['puntos'] and (p['puntos'][0]['lat'] != p['puntos'][-1]['lat'] or p['puntos'][0]['lon'] != p['puntos'][-1]['lon']):
            coord_strings.append(f"{p['puntos'][0]['lon']},{p['puntos'][0]['lat']},0")
            
        kml.append("            " + " ".join(coord_strings))
        kml.append('          </coordinates>')
        kml.append('        </LinearRing>')
        kml.append('      </outerBoundaryIs>')
        kml.append('    </Polygon>')
        kml.append('  </Placemark>')
        
    kml.append('</Document>')
    kml.append('</kml>')
    return "\n".join(kml)


def importar_kml_data(xml_content):
    """Parsea archivos KML y registra sus polígonos de forma transaccional."""
    import xml.etree.ElementTree as ET
    try:
        # Si el contenido es binario
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode('utf-8', errors='ignore')
        root = ET.fromstring(xml_content)
    except Exception as e:
        return False, f"XML malformado: {e}"
        
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"
        
    placemarks = root.findall(f".//{ns}Placemark")
    if not placemarks:
        return False, "No se encontraron elementos <Placemark> en el KML."
        
    poligonos_importados = 0
    for pm in placemarks:
        name_el = pm.find(f"{ns}name")
        nombre = name_el.text if name_el is not None else f"Polígono KML {poligonos_importados + 1}"
        
        desc_el = pm.find(f"{ns}description")
        descripcion = desc_el.text if desc_el is not None else ""
        
        coord_el = pm.find(f".//{ns}coordinates")
        if coord_el is None or not coord_el.text.strip():
            continue
            
        peso = 0.0
        unidad = "Exposición"
        color = "#ff5722"
        
        ext_data = pm.find(f"{ns}ExtendedData")
        if ext_data is not None:
            for data in ext_data.findall(f"{ns}Data"):
                data_name = data.get("name")
                val_el = data.find(f"{ns}value")
                if val_el is not None and val_el.text:
                    if data_name == "peso":
                        try:
                            peso = float(val_el.text)
                        except ValueError:
                            pass
                    elif data_name == "unidad":
                        unidad = val_el.text
                        
        style = pm.find(f".//{ns}Style")
        if style is not None:
            poly_style = style.find(f"{ns}PolyStyle")
            if poly_style is not None:
                color_el = poly_style.find(f"{ns}color")
                if color_el is not None and color_el.text:
                    kml_col = color_el.text.strip()
                    # aabbggrr -> hex #rrggbb
                    if len(kml_col) == 8:
                        color = f"#{kml_col[6:8]}{kml_col[4:6]}{kml_col[2:4]}"
                        
        # Procesar vértices
        pts_str = coord_el.text.strip().split()
        puntos = []
        for pt in pts_str:
            parts = pt.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    puntos.append((lat, lon))
                except ValueError:
                    continue
                    
        if len(puntos) >= 3:
            if add_poligono(nombre, descripcion, peso, unidad, puntos, color):
                poligonos_importados += 1
                
    return True, f"Se importaron {poligonos_importados} polígonos del KML con éxito."

