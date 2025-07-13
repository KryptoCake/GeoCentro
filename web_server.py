import os
import sqlite3
from flask import Flask, jsonify, render_template, request
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='.') # Look for templates in the root project folder

# Get the absolute path to the database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sismos.db')

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Serves the main HTML page."""
    # The template is in the same directory as the script
    return render_template('index.html')

@app.route('/api/sismos')
def get_sismos():
    """API endpoint to get seismic data with filters."""
    try:
        conn = get_db_connection()
        
        query = "SELECT * FROM terremotos WHERE 1=1"
        params = []

        # Default to last 10 days
        end_date_str = request.args.get('end_date')
        start_date_str = request.args.get('start_date')

        if not end_date_str:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        if not start_date_str:
            start_date = end_date - timedelta(days=10)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        query += " AND fecha BETWEEN ? AND ?"
        params.append(start_date.strftime('%Y-%m-%d'))
        params.append(end_date.strftime('%Y-%m-%d'))

        # Region filter
        region = request.args.get('region')
        if region and region != 'all':
            query += " AND region = ?"
            params.append(region)

        # Depth filter
        min_depth = request.args.get('min_depth', type=float)
        max_depth = request.args.get('max_depth', type=float)
        if min_depth is not None:
            query += " AND profundidad_km >= ?"
            params.append(min_depth)
        if max_depth is not None:
            query += " AND profundidad_km <= ?"
            params.append(max_depth)

        # Magnitude filter
        min_magnitude = request.args.get('min_magnitude', type=float)
        max_magnitude = request.args.get('max_magnitude', type=float)
        if min_magnitude is not None:
            query += " AND magnitud_richter >= ?"
            params.append(min_magnitude)
        if max_magnitude is not None:
            query += " AND magnitud_richter <= ?"
            params.append(max_magnitude)

        query += " ORDER BY fecha DESC, hora DESC"
        
        sismos = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(ix) for ix in sismos])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/regions')
def get_regions():
    """API endpoint to get unique regions for filtering."""
    try:
        conn = get_db_connection()
        regions = conn.execute('SELECT DISTINCT region FROM terremotos ORDER BY region').fetchall()
        conn.close()
        return jsonify([r['region'] for r in regions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask web server...")
    print(f"Go to http://127.0.0.1:5000 to see the map.")
    app.run(debug=True)
