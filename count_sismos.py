import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sismos.db')

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM terremotos')
    count = cursor.fetchone()[0]
    print(f'Total records in database: {count}')
    conn.close()
except sqlite3.Error as e:
    print(f'Database error: {e}')
except Exception as e:
    print(f'An unexpected error occurred: {e}')
