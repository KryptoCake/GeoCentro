import os
import sqlite3
from bs4 import BeautifulSoup
import re

def run_task():
    """
    This task parses seismic data from a local HTML file (lista de sismos.txt)
    and stores it in a SQLite database, avoiding duplicate entries.
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', 'sismos.db')
    # Path to the local file provided by the user
    local_file_path = 'C:/Users/PC/OneDrive/Documentos/compartida/lista de sismos.txt'

    print(f"    - Parsing local file: {local_file_path}")

    try:
        # 1. Initialize Database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS terremotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            hora TEXT,
            latitud REAL,
            longitud REAL,
            profundidad_km REAL,
            magnitud_richter REAL,
            region TEXT,
            UNIQUE(fecha, hora, latitud, longitud)
        )
        """)
        conn.commit()
        conn.close()
        print("    - Database initialized successfully.")

        # 2. Read and parse the local file
        with open(local_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        pre_tags = soup.find_all('pre')
        
        if not pre_tags:
            print("    [!] No <pre> tags found in the file.")
            return

        # Re-connect to DB for insertion
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        new_records_count = 0
        
        for pre in pre_tags:
            # Get the text and split into lines, removing empty ones
            lines = [line.strip() for line in pre.get_text().strip().split('\n') if line.strip()]
            
            if len(lines) == 2:
                data_line = lines[0]
                region = lines[1]
                
                # Split the data line by multiple spaces
                parts = re.split(r'\s+', data_line)
                
                if len(parts) >= 6:
                    fecha = parts[0]
                    hora = parts[1]
                    lat = float(parts[2])
                    lon = float(parts[3])
                    prof = float(parts[4])
                    mag = float(parts[5])
                    
                    # 4. Insert new records into the database
                    cursor.execute("""
                    INSERT OR IGNORE INTO terremotos (fecha, hora, latitud, longitud, profundidad_km, magnitud_richter, region)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (fecha, hora, lat, lon, prof, mag, region))
                    
                    if cursor.rowcount > 0:
                        new_records_count += 1

        conn.commit()
        conn.close()
        
        if new_records_count > 0:
            print(f"    - Success! Added {new_records_count} new seismic records from the local file.")
        else:
            print("    - No new seismic records found in the local file to add.")
            
        print("    - Task 'scrape_ineter_sismos' finished.")

    except FileNotFoundError:
        print(f"    [!] Error: The file was not found at {local_file_path}")
    except sqlite3.Error as e:
        print(f"    [!] Database error: {e}")
    except Exception as e:
        print(f"    [!] An unexpected error occurred: {e}")

