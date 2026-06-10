#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
Script de Migración de Sismos Históricos (2016-2017) para GeoCentro
================================================================================
Este script lee el dump SQL de MySQL 'b8_18981120_Events.sql', procesa la tabla
'evento', limpia y transforma sus registros, e importa la información histórica
directamente a la base de datos SQLite de GeoCentro (geocentro.db).
================================================================================
"""

import os
import re
import sys
import hashlib
import sqlite3
from datetime import datetime

# Asegurar salida UTF-8 en consola
sys.stdout.reconfigure(encoding='utf-8')

# Importar base de datos local
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import database

SQL_FILE = os.path.join("backups", "b8_18981120_Events.sql")

def parse_coordinate(coord_str):
    """
    Convierte coordenadas en cadena (ej: '11.56N' o '85.58W') a floats con signo.
    Norte/Este son positivos, Sur/Oeste son negativos.
    """
    coord_str = coord_str.upper().strip()
    sign = 1.0
    if coord_str.endswith('S') or coord_str.endswith('W') or coord_str.startswith('-'):
        sign = -1.0
    clean_val = coord_str.replace('N', '').replace('S', '').replace('E', '').replace('W', '').replace(':', '.').strip()
    return float(clean_val) * sign

def parse_magnitude(mag_str):
    """
    Separa una cadena de magnitud (ej: '2.3MW' o '3.4ML') en valor numérico (float)
    y su respectivo tipo (ej: 'MW', 'ML').
    """
    mag_str = mag_str.strip().upper()
    mag_match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Z]+)?$", mag_str)
    if mag_match:
        val = float(mag_match.group(1))
        m_type = mag_match.group(2) or "ML"
        return val, m_type
    try:
        return float(mag_str), "ML"
    except ValueError:
        return 0.0, "ML"

def fix_mojibake(text):
    """
    Repara el doble/triple encoding UTF-8/Latin1 (mojibake) común en dumps antiguos.
    Ej: 'Cerca del VolcÃƒÆ’Ã‚Â¡n Concepcion' -> 'Cerca del Volcán Concepcion'.
    """
    for _ in range(4):
        try:
            candidate = text.encode('latin1').decode('utf-8')
            if candidate == text:
                break
            text = candidate
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                candidate = text.encode('cp1252').decode('utf-8')
                if candidate == text:
                    break
                text = candidate
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
    # Corregir comillas simples escapadas al estilo SQL
    text = text.replace("''", "'")
    return " ".join(text.split())

def determine_country(desc):
    """
    Clasifica el país basado en la descripción del sismo.
    Dado el contexto de INETER (Nicaragua), aplica heurísticas locales.
    """
    desc_lower = desc.lower()
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
    
    # Palabras clave locales de Nicaragua en la base de datos INETER
    nicaragua_keywords = [
        'momotombo', 'cerro negro', 'concepcion', 'concepción', 'cosigüina',
        'telica', 'chinandega', 'corinto', 'managua', 'león', 'leon', 'poneloya',
        'puerto sandino', 'san juan del sur', 'masachapa', 'el sauce', 'apoyo',
        'nindirí', 'nindirã\xad', 'ticuantepe', 'masaya', 'astillero', 'la boquita',
        'casares', 'estero real', 'san cristóbal', 'san cristã³bal', 'volcan', 'volcán'
    ]
    for kw in nicaragua_keywords:
        if kw in desc_lower:
            return 'Nicaragua'
            
    return 'Otros'

def run_migration():
    print(f"=== Iniciando Migración de Sismos Históricos (2016-2017) ===")
    if not os.path.exists(SQL_FILE):
        print(f"ERROR: No se encontró el archivo SQL en: {SQL_FILE}")
        return False
        
    print(f"Leyendo archivo SQL: {SQL_FILE}")
    
    # Regex para capturar valores individuales de inserts de la tabla evento
    # Formato: ('Fecha', 'Hora_local', 'Latitud', 'Longitud', 'Profundidad', 'Magnitud', 'Region', ID, HORA_INSERTADO)
    value_pattern = re.compile(
        r"\("
        r"'(\d{2}/\d{2}/\d{2})',\s*"  # 1: Fecha (YY/MM/DD)
        r"'(\d{2}:\d{2}:\d{2})',\s*"  # 2: Hora_local (HH:MM:SS)
        r"'([^']*)',\s*"              # 3: Latitud (ej: 11.56N)
        r"'([^']*)',\s*"              # 4: Longitud (ej: 85.58W)
        r"'([^']*)',\s*"              # 5: Profundidad (ej: 5.6)
        r"'([^']*)',\s*"              # 6: Magnitud (ej: 2.3MW)
        r"'(.*)',\s*"                 # 7: Region (con posible mojibake)
        r"(\d+),\s*"                  # 8: ID original
        r"(NULL|'[^']*')"             # 9: HORA_INSERTADO (opcional)
        r"\)"
    )

    total_processed = 0
    total_inserted = 0
    total_skipped = 0
    
    # Llevar conteo previo en SQLite
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sismos")
    before_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"Total de sismos registrados actualmente en SQLite: {before_count}")
    
    with open(SQL_FILE, 'r', encoding='latin1') as f:
        in_evento_data = False
        for line_num, line in enumerate(f, 1):
            # Control de flujo para leer únicamente datos de la tabla evento
            if 'INSERT INTO `evento` ' in line:
                in_evento_data = True
            elif 'INSERT INTO ' in line:
                in_evento_data = False
                
            if in_evento_data:
                matches = value_pattern.findall(line)
                for m in matches:
                    total_processed += 1
                    fecha_raw, hora_raw, lat_raw, lon_raw, depth_raw, mag_raw, region_raw, orig_id, _ = m
                    
                    try:
                        # 1. Formatear Fecha a YYYY-MM-DD
                        fecha_formatted = f"20{fecha_raw.replace('/', '-')}"
                        
                        # 2. Formatear Coordenadas
                        lat = parse_coordinate(lat_raw)
                        lon = parse_coordinate(lon_raw)
                        
                        # 3. Formatear Profundidad y Magnitud
                        depth = int(float(depth_raw))
                        mag, mag_type = parse_magnitude(mag_raw)
                        
                        # 4. Corregir Mojibake en Región
                        clean_region = fix_mojibake(region_raw)
                        
                        # 5. Determinar País
                        country = determine_country(clean_region)
                        
                        # 6. Intentar guardar en SQLite
                        inserted = database.save_sismo(
                            fecha_utc=fecha_formatted,
                            hora_utc=hora_raw,
                            latitud=lat,
                            longitud=lon,
                            profundidad=depth,
                            magnitud=mag,
                            tipo=mag_type,
                            descripcion=clean_region,
                            pais=country
                        )
                        
                        if inserted:
                            total_inserted += 1
                            if total_inserted % 500 == 0:
                                print(f"-> {total_inserted} registros importados exitosamente...")
                        else:
                            total_skipped += 1
                            
                    except Exception as e:
                        print(f"Error procesando registro ID original {orig_id}: {e}")
                        total_skipped += 1

    # Recuento final en SQLite
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sismos")
    after_count = cursor.fetchone()[0]
    conn.close()

    print("\n=== Resumen de la Migración ===")
    print(f"Registros procesados del dump SQL: {total_processed}")
    print(f"Registros insertados en SQLite:    {total_inserted}")
    print(f"Registros omitidos (duplicados):   {total_skipped}")
    print(f"Conteo en SQLite antes de migrar:  {before_count}")
    print(f"Conteo en SQLite después de migrar: {after_count}")
    print(f"Incremento total de sismos:        {after_count - before_count}")
    print("================================")
    
    return True

if __name__ == "__main__":
    run_migration()
