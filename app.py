import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

# LOCAL DEDICATED STORAGE
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Airflow API Configuration
AIRFLOW_API_URL = os.getenv('AIRFLOW_API_URL', 'http://localhost:8080/api/v1/dags/etl_gokwik_csv_to_bronze/dagRuns')
AIRFLOW_USER = os.getenv('AIRFLOW_USERNAME', 'airflow')
AIRFLOW_PASS = os.getenv('AIRFLOW_PASSWORD', 'airflow')


@app.route('/')
def index():
    return render_template('index.html', bucket_name="Local Shared Volume")


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Empty file selected.'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Only .csv files are supported.'}), 400

    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = secure_filename(file.filename)
        new_filename = f"{timestamp}_{safe_filename}"
        
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)

        # 1. Save locally to shared volume
        file.save(file_path)

        # 2. [OPTIONAL] Airflow DAG trigger via REST API
        try:
             dag_run_id = f"manual_upload_{timestamp}"
             payload = {
                 "dag_run_id": dag_run_id,
                 "conf": {
                     "local_file": new_filename,
                     "original_filename": file.filename
                 }
             }
             # Uncomment to enable trigger
             # requests.post(AIRFLOW_API_URL, auth=(AIRFLOW_USER, AIRFLOW_PASS), json=payload, timeout=10)
        except Exception as api_err:
             print(f"Airflow API trigger skipped/failed: {api_err}")

        return jsonify({
            'success': True,
            'message': f'File successfully saved locally to shared volume as: {new_filename}',
            'filename': new_filename
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    print(f"Server started on http://localhost:5000 | Saving files to: {UPLOAD_FOLDER}")
    app.run(debug=True, port=5000, host="0.0.0.0")
