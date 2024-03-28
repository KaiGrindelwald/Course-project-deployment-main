#/routes/music_upload.py
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.utils import secure_filename
import os
import psycopg2
import base64

audio_blueprint = Blueprint('audio', __name__)

# Assuming you've properly configured DATABASE_URL in your environment variables

ALLOWED_EXTENSIONS = {'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@audio_blueprint.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "You must be logged in to upload audios."}), 401

    username = session['username']

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "No selected file or file type is not allowed"}), 400

    audio_blob = file.read()

    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cur.fetchone()[0]

        filename = secure_filename(file.filename)

        cur.execute(
            "INSERT INTO audio_library (user_id, audio_path, audio_blob) VALUES (%s, %s, %s)",
            (user_id, filename, audio_blob)
        )
        conn.commit()

        return jsonify({"status": "success", "message": "Audio successfully uploaded"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": "Failed to upload audio: " + str(e)}), 500
    finally:
        cur.close()
        conn.close()

@audio_blueprint.route('/fetch_user_audios', methods=['GET'])
def fetch_user_audios():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "You must be logged in to fetch audios."}), 401

    username = session['username']

    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT id, audio_path FROM audio_library INNER JOIN users ON audio_library.user_id = users.id WHERE users.username = %s", (username,))
        audios = cur.fetchall()

        # Convert to JSON-friendly format
        audio_data = [{"id": audio[0], "audio_path": audio[1]} for audio in audios]
        return jsonify({"status": "success", "audios": audio_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to fetch audios: " + str(e)}), 500
    finally:
        cur.close()
        conn.close()
