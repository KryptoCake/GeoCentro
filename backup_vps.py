#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
Script de Respaldo GeoCentro (Python)
================================================================================
Este script realiza un respaldo seguro de la base de datos SQLite (usando la API 
online .backup()) y comprime los archivos de código fuente, aplicando una
política de retención de 7 días.
Es compatible tanto con entornos Windows (desarrollo) como Linux (producción).
================================================================================
"""

import os
import shutil
import sqlite3
import tarfile
from datetime import datetime
import glob
import urllib.request

# Configuración por defecto de Rutas (Producción VPS)
BACKUP_DIR = "/var/www/geocentro/backups"
SRC_DIR = "/var/www/geocentro"
DB_FILE = "/var/www/geocentro/geocentro.db"
RETENTION_DAYS = 7

# Configuración de Telegram (Opcional)
# Configura tu Bot Token y Chat ID para recibir tus respaldos directo en Telegram
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Auto-ajuste de rutas para desarrollo local (si no existe la ruta de producción)
if not os.path.exists(SRC_DIR):
    SRC_DIR = os.path.abspath(os.path.dirname(__file__))
    BACKUP_DIR = os.path.join(SRC_DIR, "backups")
    DB_FILE = os.path.join(SRC_DIR, "geocentro.db")

def run_backup():
    print(f"=== Iniciando Respaldo de GeoCentro - {datetime.now()} ===")
    
    # 1. Crear el directorio de respaldos si no existe
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"geocentro_backup_{timestamp}.tar.gz"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    temp_db_name = "geocentro_temp.db"
    temp_db_path = os.path.join(BACKUP_DIR, temp_db_name)
    
    # 2. Respaldo seguro de SQLite en caliente (Online Backup API)
    # Evita copiar el archivo de base de datos en medio de una transacción incompleta.
    print("1. Realizando copia segura en caliente de la base de datos...")
    db_backed_up = False
    try:
        if os.path.exists(DB_FILE):
            src_conn = sqlite3.connect(DB_FILE)
            dst_conn = sqlite3.connect(temp_db_path)
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
            db_backed_up = True
            print("-> Copia de base de datos creada con éxito.")
        else:
            print(f"ADVERTENCIA: No se encontró la base de datos en {DB_FILE}. Se respaldará sin DB.")
    except Exception as e:
        print(f"ERROR: Falló el respaldo de la base de datos: {e}")
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        return False
        
    # 3. Compresión del código fuente y de la base de datos respaldada
    # Excluimos las carpetas pesadas/temporales para no inflar el tamaño
    print("2. Comprimiendo archivos y base de datos...")
    try:
        exclude_dirs = {
            os.path.join(SRC_DIR, "venv"),
            os.path.join(SRC_DIR, ".git"),
            os.path.join(SRC_DIR, "backups"),
            os.path.join(SRC_DIR, "__pycache__"),
            os.path.join(SRC_DIR, "implementation_plans_for_agents")
        }
        
        with tarfile.open(backup_path, "w:gz") as tar:
            # Recorrer recursivamente el directorio del código fuente
            for root, dirs, files in os.walk(SRC_DIR):
                # Modificar dirs in-place para que os.walk no entre en carpetas excluidas
                dirs[:] = [d for d in dirs if os.path.join(root, d) not in exclude_dirs]
                
                for file in files:
                    full_path = os.path.join(root, file)
                    # No incluir el archivo temporal de base de datos directamente en el recorrido
                    if full_path == temp_db_path:
                        continue
                    # Obtener la ruta relativa para el interior del tar.gz
                    rel_path = os.path.relpath(full_path, SRC_DIR)
                    tar.add(full_path, arcname=rel_path)
            
            # Agregar la base de datos temporal dentro de la carpeta 'backups' simulada
            if db_backed_up and os.path.exists(temp_db_path):
                tar.add(temp_db_path, arcname=os.path.join("backups", "geocentro.db"))
                
        print(f"-> Respaldo comprimido creado: {backup_path} ({os.path.getsize(backup_path) / 1024:.1f} KB)")
    except Exception as e:
        print(f"ERROR: Falló la compresión del respaldo: {e}")
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return False
    finally:
        # Eliminar el archivo de base de datos temporal
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
            
    # 4. Envío opcional a Telegram (Multipart Form-Data nativo sin dependencias externas)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("3. Subiendo respaldo a Telegram...")
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            with open(backup_path, 'rb') as f:
                file_bytes = f.read()
                
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            parts = []
            
            parts.append(f'--{boundary}')
            parts.append('Content-Disposition: form-data; name="chat_id"\r\n')
            parts.append(TELEGRAM_CHAT_ID)
            
            parts.append(f'--{boundary}')
            parts.append('Content-Disposition: form-data; name="caption"\r\n')
            parts.append(f"📦 *GeoCentro Backup* - {timestamp} (Retención: {RETENTION_DAYS} días)")
            
            parts.append(f'--{boundary}')
            parts.append('Content-Disposition: form-data; name="parse_mode"\r\n')
            parts.append("Markdown")
            
            parts.append(f'--{boundary}')
            parts.append(f'Content-Disposition: form-data; name="document"; filename="{backup_name}"')
            parts.append('Content-Type: application/gzip\r\n')
            parts.append(file_bytes)
            
            body = b''
            for part in parts:
                if isinstance(part, str):
                    body += part.encode('utf-8') + b'\r\n'
                else:
                    body += part + b'\r\n'
            body += f'--{boundary}--'.encode('utf-8') + b'\r\n'
            
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    'Content-Type': f'multipart/form-data; boundary={boundary}',
                    'Content-Length': str(len(body)),
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response.read()
                print("-> Respaldo enviado exitosamente a Telegram.")
        except Exception as e:
            print(f"ADVERTENCIA: No se pudo subir el respaldo a Telegram: {e}")
            
    # 5. Rotación de respaldos (Eliminar los mayores a RETENTION_DAYS días)
    print(f"4. Aplicando política de rotación (Eliminando respaldos de más de {RETENTION_DAYS} días)...")
    try:
        now = datetime.now()
        backups = glob.glob(os.path.join(BACKUP_DIR, "geocentro_backup_*.tar.gz"))
        for b_file in backups:
            mtime = datetime.fromtimestamp(os.path.getmtime(b_file))
            age_days = (now - mtime).days
            if age_days > RETENTION_DAYS:
                os.remove(b_file)
                print(f"-> Respaldo antiguo eliminado: {os.path.basename(b_file)} ({age_days} días de antigüedad)")
    except Exception as e:
        print(f"ADVERTENCIA: No se pudo completar la rotación de archivos: {e}")
        
    print(f"=== Respaldo Finalizado con Éxito - {datetime.now()} ===")
    return True

if __name__ == "__main__":
    run_backup()
