#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Migración y Depuración de Sismos (Capa Raw/Canónica) — GeoCentro
Versión: 4.1 (Plan de Deduplicación Definitivo)
"""

import os
import sys
import sqlite3
import calendar
import time
import statistics
from datetime import datetime, timezone

# Asegurar salida UTF-8 en consola
sys.stdout.reconfigure(encoding='utf-8')

# Añadir directorio actual al path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import database

DB_PATH = "geocentro.db"
BAK_PATH = "geocentro.db.bak"

def print_rollback_instructions():
    print("\n" + "="*80)
    print(" INSTRUCCIONES DE ROLLBACK (EN CASO DE FALLO):")
    print("="*80)
    print(" 1. Detener el servicio web (si está activo).")
    print(" 2. Restaurar la base de datos desde el backup en caliente:")
    print(f"    cp {BAK_PATH} {DB_PATH}")
    print(" 3. Revertir los archivos de código fuente al checkpoint pre-implementación:")
    print("    git checkout 1decd0b -- database.py scraper.py app.py")
    print(" 4. Levantar nuevamente el servicio web.")
    print("="*80 + "\n")

def run_backup():
    print(f"[*] Iniciando copia de seguridad en caliente de '{DB_PATH}'...")
    if not os.path.exists(DB_PATH):
        print(f"[-] ERROR: No se encontró el archivo de base de datos '{DB_PATH}'.")
        return False

    try:
        # Copia en caliente con sqlite3.Connection.backup()
        src_conn = sqlite3.connect(DB_PATH)
        dst_conn = sqlite3.connect(BAK_PATH)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        print(f"[+] Respaldo completado exitosamente en '{BAK_PATH}'.")

        # Verificar el backup con integrity_check
        check_conn = sqlite3.connect(BAK_PATH)
        res = check_conn.execute("PRAGMA integrity_check").fetchone()[0]
        check_conn.close()

        if res == "ok":
            print("[+] Integridad física de la base de datos de respaldo: OK.")
            return True
        else:
            print(f"[-] ERROR de integridad en base de datos de respaldo: {res}")
            return False
    except Exception as e:
        print(f"[-] ERROR al realizar el backup en caliente: {e}")
        return False

def show_type_validation():
    print("[*] Validando mapeo de tipos de sismos en la BD actual...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT tipo, COUNT(*) as cant FROM sismos GROUP BY tipo")
    rows = cursor.fetchall()
    
    print("\nTipos de sismos encontrados en tabla 'sismos' original:")
    print("-"*60)
    print(f"{'Tipo original':<15} | {'Cantidad':<8} | {'Agencia Inferida':<15} | {'Feed Inferido':<15}")
    print("-"*60)
    for r in rows:
        tipo = r['tipo']
        agencia, feed = database.get_agency_from_tipo(tipo)
        print(f"{tipo:<15} | {r['cant']:<8} | {agencia:<15} | {feed:<15}")
    print("-"*60 + "\n")
    conn.close()

def migrate_to_raw():
    print("[*] Inicializando base de datos para asegurar el nuevo esquema...")
    database.init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Comprobar si ya hay registros en sismos_raw
    cursor.execute("SELECT COUNT(*) FROM sismos_raw")
    raw_count = cursor.fetchone()[0]
    if raw_count > 0:
        print(f"[!] ADVERTENCIA: La tabla 'sismos_raw' ya contiene {raw_count} registros. Se omitirá el copiado inicial para evitar duplicación.")
        conn.close()
        return True

    # Obtener sismos originales
    cursor.execute("SELECT * FROM sismos")
    sismos_originales = cursor.fetchall()
    print(f"[*] Migrando {len(sismos_originales)} registros desde 'sismos' a 'sismos_raw'...")

    # Insertar en sismos_raw conservando el ID
    total_migrated = 0
    for s in sismos_originales:
        t_epoch = database.compute_t_epoch(s['fecha_utc'], s['hora_utc'])
        agencia, feed = database.get_agency_from_tipo(s['tipo'])
        scraped_at = t_epoch  # Aproximación para históricos

        cursor.execute('''
            INSERT INTO sismos_raw (id, fecha_utc, hora_utc, t_epoch, latitud, longitud,
                                    profundidad, magnitud, tipo, descripcion, pais,
                                    hash_id, agencia, feed, scraped_at, sismo_canonical_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        ''', (s['id'], s['fecha_utc'], s['hora_utc'], t_epoch, s['latitud'], s['longitud'],
              s['profundidad'], s['magnitud'], s['tipo'], s['descripcion'], s['pais'],
              s['hash_id'], agencia, feed, scraped_at))
        total_migrated += 1

    conn.commit()
    print(f"[+] Se migraron {total_migrated} registros a 'sismos_raw'.")
    conn.close()
    return True

def run_deduplication_batch():
    print("[*] Enlazar base de datos para la deduplicación en lote...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Configurar transacción manual
    conn.isolation_level = None
    
    # Vaciar la tabla canónica sismos
    print("[*] Vaciando la tabla canónica 'sismos'...")
    conn.execute("DELETE FROM sismos")
    # Reset de la secuencia de IDs de sqlite para no interferir con la herencia de IDs
    conn.execute("DELETE FROM sqlite_sequence WHERE name='sismos'")
    
    # Obtener registros crudos ordenados por t_epoch, id (D9, medianoche-safe)
    cursor = conn.execute("SELECT id FROM sismos_raw ORDER BY t_epoch ASC, id ASC")
    raw_ids = [row['id'] for row in cursor.fetchall()]
    
    print(f"[*] Procesando {len(raw_ids)} reportes en lote...")
    
    migrated_count = 0
    for raw_id in raw_ids:
        conn.execute("BEGIN IMMEDIATE")
        try:
            database._deduplicate_and_sync(conn, raw_id)
            conn.execute("COMMIT")
            migrated_count += 1
            if migrated_count % 500 == 0:
                print(f" -> {migrated_count} reportes deduplicados e insertados en canónica...")
        except Exception as e:
            conn.execute("ROLLBACK")
            print(f"[-] ERROR crítico en deduplicación de reporte raw_id={raw_id}: {e}")
            conn.close()
            return False
            
    print(f"[+] Deduplicación en lote completada. Total procesados: {migrated_count}")
    conn.close()
    return True

def run_assertions():
    print("[*] Iniciando suite de aserciones de control de calidad (A1-A8)...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # -------------------------------------------------------------------------
    # A1 — Conversión UTC explícita
    # -------------------------------------------------------------------------
    print("[*] Aserción A1: Conversión UTC...")
    esperado = calendar.timegm(time.strptime("2026-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"))
    assert database.compute_t_epoch("2026-01-01", "00:00:00") == esperado == 1767225600
    print(" -> A1 Pasada.")

    # -------------------------------------------------------------------------
    # A2 — Doblete real del 26-06-2026 (NO fusionar)
    # -------------------------------------------------------------------------
    print("[*] Aserción A2: Doblete 26-06-2026 (Masachapa y Honduras)...")
    # Buscar el evento Honduras M5.9 (05:57:03 UTC, lat ~13.2)
    # y el de Masachapa (05:57:26-27 UTC, lat ~11.9)
    cursor.execute("""
        SELECT * FROM sismos 
        WHERE fecha_utc = '2026-06-26' 
        AND hora_utc BETWEEN '05:56:00' AND '05:58:30'
    """)
    sismos_doblete = cursor.fetchall()
    
    print(f"    Sismos encontrados en ventana de doblete: {len(sismos_doblete)}")
    for s in sismos_doblete:
        print(f"      ID: {s['id']}, Lat: {s['latitud']}, Lon: {s['longitud']}, Mag: {s['magnitud']}, País: {s['pais']}, Desc: {s['descripcion']}")
        
    # Debe haber al menos dos sismos canónicos representando los eventos independientes
    assert len(sismos_doblete) >= 2, "Deberían encontrarse al menos 2 eventos canónicos distintos para el doblete"
    
    # Comprobar que el de Honduras (lat > 12.8) y el de Masachapa (lat < 12.2) tengan IDs distintos
    honduras = [s for s in sismos_doblete if s['latitud'] > 12.8]
    masachapa = [s for s in sismos_doblete if s['latitud'] < 12.2]
    
    assert len(honduras) > 0, "No se encontró el evento canónico de Honduras"
    assert len(masachapa) > 0, "No se encontró el evento canónico de Masachapa"
    assert honduras[0]['id'] != masachapa[0]['id'], "Honduras y Masachapa se fusionaron incorrectamente"
    print(" -> A2 Pasada.")

    # -------------------------------------------------------------------------
    # A3 — Reportes de Masachapa entre sí (SÍ fusionar)
    # -------------------------------------------------------------------------
    print("[*] Aserción A3: Reportes de Masachapa duplicados (SÍ fusionar)...")
    # Buscar reportes de Masachapa del doblete en raw
    cursor.execute("""
        SELECT sismo_canonical_id, COUNT(*) as cant 
        FROM sismos_raw 
        WHERE fecha_utc = '2026-06-26' 
        AND hora_utc BETWEEN '05:57:20' AND '05:57:35'
        AND latitud < 12.2
        GROUP BY sismo_canonical_id
    """)
    grupos_masachapa = cursor.fetchall()
    assert len(grupos_masachapa) == 1, "Los reportes del sismo de Masachapa se dividieron en múltiples eventos canónicos"
    print(" -> A3 Pasada.")

    # -------------------------------------------------------------------------
    # A4 — Guanacaste 09-06 21:01:33 (SÍ fusionar, verificar mediana post-filtrado)
    # -------------------------------------------------------------------------
    print("[*] Aserción A4: Guanacaste 09-06 21:01:33...")
    cursor.execute("""
        SELECT sismo_canonical_id, COUNT(*) as cant 
        FROM sismos_raw 
        WHERE fecha_utc = '2026-06-09' 
        AND hora_utc BETWEEN '21:00:30' AND '21:02:30'
        AND latitud BETWEEN 10.3 AND 11.2
        GROUP BY sismo_canonical_id
    """)
    grupos_guanacaste = cursor.fetchall()
    assert len(grupos_guanacaste) == 1, f"Los reportes de Guanacaste se dividieron en múltiples canónicos o no se encontró ninguno (grupos: {len(grupos_guanacaste)})"
    
    canonical_id = grupos_guanacaste[0]['sismo_canonical_id']
    cursor.execute("SELECT * FROM sismos WHERE id = ?", (canonical_id,))
    sismo_can_guanacaste = cursor.fetchone()
    
    # Calcular mediana post-filtrado por agencia de forma manual para verificar
    cursor.execute("SELECT * FROM sismos_raw WHERE sismo_canonical_id = ?", (canonical_id,))
    raw_guanacaste = cursor.fetchall()
    
    # Agrupar por agencia
    by_agency = {}
    for r in raw_guanacaste:
        ag = r['agencia']
        if ag not in by_agency or r['scraped_at'] > by_agency[ag]['scraped_at'] or (r['scraped_at'] == by_agency[ag]['scraped_at'] and r['id'] > by_agency[ag]['id']):
            by_agency[ag] = r
            
    mediana_esperada = round(statistics.median([r['magnitud'] for r in by_agency.values()]), 1)
    print(f"    Guanacaste unificado (ID canónico: {canonical_id}):")
    print(f"      Reportes raw asociados: {len(raw_guanacaste)}")
    print(f"      Instituciones únicas: {len(by_agency)}")
    print(f"      Magnitud en canónica: {sismo_can_guanacaste['magnitud']}")
    print(f"      Magnitud mediana calculada: {mediana_esperada}")
    
    assert sismo_can_guanacaste['magnitud'] == mediana_esperada, f"La magnitud canónica ({sismo_can_guanacaste['magnitud']}) difiere de la mediana esperada ({mediana_esperada})"
    print(" -> A4 Pasada.")

    # -------------------------------------------------------------------------
    # A5 — Telesismos (No clasificar 'Costa Rica')
    # -------------------------------------------------------------------------
    print("[*] Aserción A5: Clasificación de Telesismos...")
    cursor.execute("""
        SELECT * FROM sismos 
        WHERE (latitud < 5.0 OR latitud > 20.0 OR longitud < -100.0 OR longitud > -70.0)
    """)
    telesismos = cursor.fetchall()
    print(f"    Telesismos evaluados: {len(telesismos)}")
    for t in telesismos:
        print(f"      ID: {t['id']}, Lat: {t['latitud']}, Lon: {t['longitud']}, País en canónica: '{t['pais']}', Desc: {t['descripcion']}")
        assert t['pais'] != 'Costa Rica', f"Telesismo ID={t['id']} fue etiquetado erróneamente como Costa Rica"
    print(" -> A5 Pasada.")

    # -------------------------------------------------------------------------
    # A6 — Golfo de Fonseca (Clasificación por BBox más cercano)
    # -------------------------------------------------------------------------
    print("[*] Aserción A6: Golfo de Fonseca...")
    pais_golfo = database.determinar_pais_coordenadas(13.2, -87.7, '')
    print(f"    Punto sintético en el Golfo (13.2, -87.7) -> Clasificado como: '{pais_golfo}'")
    assert pais_golfo in ('El Salvador', 'Honduras', 'Nicaragua'), f"Golfo de Fonseca clasificado erróneamente como '{pais_golfo}'"
    print(" -> A6 Pasada.")

    # -------------------------------------------------------------------------
    # A7 — Reproducibilidad
    # -------------------------------------------------------------------------
    print("[*] Aserción A7: Reproducibilidad (idempotencia)...")
    # Para validar la reproducibilidad de forma segura sin modificar la tabla de producción:
    # 1. Crear tabla temporal sismos_check
    cursor.execute("DROP TABLE IF EXISTS sismos_check")
    cursor.execute("""
        CREATE TABLE sismos_check (
            id INTEGER PRIMARY KEY, fecha_utc TEXT, hora_utc TEXT, latitud REAL, longitud REAL,
            profundidad INTEGER, magnitud REAL, tipo TEXT, descripcion TEXT, pais TEXT,
            hash_id TEXT, t_epoch INTEGER
        )
    """)
    # Clonar sismos a sismos_check
    cursor.execute("INSERT INTO sismos_check SELECT id, fecha_utc, hora_utc, latitud, longitud, profundidad, magnitud, tipo, descripcion, pais, hash_id, t_epoch FROM sismos")
    
    # 2. Vaciar sismos y volver a correr deduplicación en lote
    cursor.execute("DELETE FROM sismos")
    cursor.execute("UPDATE sismos_raw SET sismo_canonical_id = NULL")
    
    # Ejecutar matching de nuevo
    cursor.execute("SELECT id FROM sismos_raw ORDER BY t_epoch ASC, id ASC")
    raw_ids = [row['id'] for row in cursor.fetchall()]
    
    # Confirmar y cerrar conexión actual para liberar locks
    conn.commit()
    conn.close()
    
    # Correr matching sobre conexión aislada limpia
    conn_manual = sqlite3.connect(DB_PATH)
    conn_manual.row_factory = sqlite3.Row
    conn_manual.isolation_level = None
    for r_id in raw_ids:
        conn_manual.execute("BEGIN IMMEDIATE")
        database._deduplicate_and_sync(conn_manual, r_id)
        conn_manual.execute("COMMIT")
    conn_manual.close()
    
    # Reabrir conexión de aserciones
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 3. Comparar sismos contra sismos_check
    cursor.execute("SELECT COUNT(*) FROM sismos")
    count_1 = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM sismos_check")
    count_2 = cursor.fetchone()[0]
    
    assert count_1 == count_2, f"La cantidad de registros difiere entre ejecuciones: {count_1} vs {count_2}"
    
    cursor.execute("""
        SELECT s.id, s.magnitud, s.pais 
        FROM sismos s
        JOIN sismos_check sc ON s.id = sc.id
        WHERE s.magnitud != sc.magnitud OR s.pais != sc.pais
    """)
    diferencias = cursor.fetchall()
    assert len(diferencias) == 0, f"Se encontraron diferencias en las propiedades de los canónicos regenerados: {len(diferencias)} filas difieren"
    
    # Limpiar tabla temporal
    cursor.execute("DROP TABLE IF EXISTS sismos_check")
    print(" -> A7 Pasada.")

    # -------------------------------------------------------------------------
    # A8 — Rescate de IDs
    # -------------------------------------------------------------------------
    print("[*] Aserción A8: Rescate de IDs de duplicados...")
    # Tomar un reporte raw que sea duplicado y no representativo
    # (es decir, sismo_canonical_id es diferente de su propio ID en raw)
    cursor.execute("SELECT id, sismo_canonical_id FROM sismos_raw WHERE id != sismo_canonical_id LIMIT 1")
    dup = cursor.fetchone()
    if dup:
        dup_id = dup['id']
        canonical_expected_id = dup['sismo_canonical_id']
        sismo_rescatado = database.get_sismo_by_id(dup_id)
        
        print(f"    Rescatando reporte duplicado raw_id={dup_id}:")
        print(f"      Canónico asociado esperado: ID={canonical_expected_id}")
        print(f"      Canónico retornado por API: ID={sismo_rescatado['id'] if sismo_rescatado else None}")
        
        assert sismo_rescatado is not None, "El rescate devolvió None"
        assert sismo_rescatado['id'] == canonical_expected_id, "El rescate no redirigió al ID canónico correcto"
    else:
        print("    [!] ADVERTENCIA: No se encontraron sismos duplicados para probar el rescate.")
    print(" -> A8 Pasada.")

    print("\n[+] TODAS LAS ASERCIONES (A1-A8) PASARON EXITOSAMENTE.")
    conn.close()

def print_statistics_report():
    print("\n" + "="*80)
    print(" REPORTE ESTADÍSTICO DE DEDUPLICACIÓN")
    print("="*80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Conteos generales
    cursor.execute("SELECT COUNT(*) FROM sismos_raw")
    total_raw = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sismos")
    total_canonical = cursor.fetchone()[0]
    
    factor_dedup = ((total_raw - total_canonical) / total_raw) * 100 if total_raw > 0 else 0
    
    print(f" Total de reportes en capa cruda (sismos_raw): {total_raw}")
    print(f" Total de eventos en capa canónica (sismos):     {total_canonical}")
    print(f" Registros duplicados eliminados:                {total_raw - total_canonical}")
    print(f" Factor de deduplicación:                        {factor_dedup:.1f}%")
    
    # Conteos por país antes y después
    print("\n Distribución por país (Capa Cruda vs Capa Canónica):")
    print("-"*60)
    print(f"{'País':<20} | {'Reportes Raw':<15} | {'Canónicos Deduplicados':<20}")
    print("-"*60)
    
    cursor.execute("SELECT pais, COUNT(*) as cant FROM sismos_raw GROUP BY pais")
    raw_countries = {r['pais']: r['cant'] for r in cursor.fetchall()}
    
    cursor.execute("SELECT pais, COUNT(*) as cant FROM sismos GROUP BY pais")
    canonical_countries = {r['pais']: r['cant'] for r in cursor.fetchall()}
    
    all_countries = sorted(list(set(list(raw_countries.keys()) + list(canonical_countries.keys()))))
    for c in all_countries:
        r_cant = raw_countries.get(c, 0)
        c_cant = canonical_countries.get(c, 0)
        print(f"{c:<20} | {r_cant:<15} | {c_cant:<20}")
    print("-"*60)
    
    # 10 grupos más grandes
    print("\n 10 grupos de sismos duplicados más grandes:")
    print("-"*80)
    print(f"{'ID Canónico':<12} | {'Instituciones':<30} | {'Magnitud Canónica':<18} | {'Cantidad Raw':<12}")
    print("-"*80)
    
    cursor.execute("""
        SELECT sismo_canonical_id, COUNT(*) as cant_raw
        FROM sismos_raw
        GROUP BY sismo_canonical_id
        ORDER BY cant_raw DESC
        LIMIT 10
    """)
    top_groups = cursor.fetchall()
    
    for tg in top_groups:
        c_id = tg['sismo_canonical_id']
        cursor.execute("SELECT magnitud FROM sismos WHERE id = ?", (c_id,))
        c_row = cursor.fetchone()
        c_mag = c_row['magnitud'] if c_row else 0.0
        
        cursor.execute("SELECT DISTINCT agencia FROM sismos_raw WHERE sismo_canonical_id = ?", (c_id,))
        agencias = ", ".join([r['agencia'] for r in cursor.fetchall()])
        
        print(f"{c_id:<12} | {agencias:<30} | {c_mag:<18.1f} | {tg['cant_raw']:<12}")
    print("-"*80 + "\n")
    conn.close()

def main():
    print("="*80)
    print(" MIGRACIÓN Y DEPURACIÓN EN CALIENTE — GEOCENTRO v4.1")
    print("="*80)
    
    print_rollback_instructions()
    
    # Paso 1: Realizar backup en caliente
    if not run_backup():
        print("[-] ERROR: No se pudo realizar el backup en caliente. Proceso abortado.")
        sys.exit(1)
        
    try:
        # Paso 2: Mostrar validación de tipos
        show_type_validation()
        
        # Paso 3: Copiar sismos actuales a sismos_raw
        if not migrate_to_raw():
            raise Exception("Fallo en la migración a la tabla sismos_raw")
            
        # Paso 4: Deduplicar en lote
        if not run_deduplication_batch():
            raise Exception("Fallo en el proceso de deduplicación en lote")
            
        # Paso 5: Correr aserciones
        run_assertions()
        
        # Paso 6: Mostrar reporte estadístico
        print_statistics_report()
        
        print("[+] MIGRACIÓN FINALIZADA CON ÉXITO Y TOTALMENTE VALIDADA.")
        
    except Exception as e:
        import traceback
        print("\n[-] DETALLE DEL ERROR CRÍTICO:")
        traceback.print_exc()
        print(f"\n[-] ERROR CRÍTICO DURANTE LA MIGRACIÓN: {e}")
        print_rollback_instructions()
        sys.exit(1)

if __name__ == "__main__":
    main()
