from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os
import datetime

app = Flask(__name__)
CORS(app)  # allow dev calls

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'reports.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lng REAL,
            type TEXT,
            description TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_conn():
    # added check_same_thread=False to avoid sqlite threading error in debug server
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@app.route("/")
def index():
    return render_template("setTarget.html")

@app.route('/report', methods=['POST'])
def report():
    data = request.get_json()

    # debug logging so we can see what's actually being posted
    print("RECEIVED REPORT RAW JSON:", data)

    lat = data.get('lat')
    lng = data.get('lng')
    hazard_type = data.get('type', 'Unknown')
    description = data.get('description', '')

    timestamp = datetime.datetime.now().isoformat()

    print("Parsed:", lat, lng, hazard_type, description)

    # sanity check
    if lat is None or lng is None:
        return jsonify({'error': 'lat and lng are required'}), 400

    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute(
            'INSERT INTO reports (lat, lng, type, description, timestamp) VALUES (?, ?, ?, ?, ?)',
            (lat, lng, hazard_type, description, timestamp)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # print full error to terminal to debug
        print("DB INSERT ERROR:", e)
        # return 500 with info
        return jsonify({'error': 'db insert failed', 'details': str(e)}), 500

    return jsonify({'message': 'Location reported successfully!'})

@app.route('/reports', methods=['GET'])
def get_reports():
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT lat, lng, type, description, timestamp FROM reports')
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        print("DB READ ERROR:", e)
        return jsonify({'error': 'db read failed', 'details': str(e)}), 500

    reports = [
        {
            'lat': r[0],
            'lng': r[1],
            'type': r[2],
            'description': r[3],
            'timestamp': r[4]
        }
        for r in rows
    ]

    return jsonify(reports)

if __name__ == '__main__':
    # force single-threaded mode to reduce sqlite weirdness:
    app.run(debug=True, threaded=False)
