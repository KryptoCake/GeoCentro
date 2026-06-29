import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geocentro.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create sismos table
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

def generate_sismo_hash(fecha_utc, hora_utc, latitud, longitud):
    # Standardize formats and coordinates to avoid rounding mismatches
    data = f"{fecha_utc.strip()}|{hora_utc.strip()}|{float(latitud):.4f}|{float(longitud):.4f}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_news_hash(titulo, url):
    data = f"{titulo.strip()}|{url.strip()}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def save_sismo(fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo, descripcion, pais):
    hash_id = generate_sismo_hash(fecha_utc, hora_utc, latitud, longitud)
    conn = get_db_connection()
    cursor = conn.cursor()
    inserted = False
    try:
        cursor.execute('''
            INSERT INTO sismos (fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo, descripcion, pais, hash_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo, descripcion, pais, hash_id))
        conn.commit()
        inserted = True
    except sqlite3.IntegrityError:
        # Duplicate entry
        inserted = False
    finally:
        conn.close()
    return inserted

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
