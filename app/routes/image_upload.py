#/routes/image_upload.py
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.utils import secure_filename
import os
import psycopg2
import base64
import traceback

image_upload_blueprint = Blueprint('image', __name__)

# Assuming you've properly configured DATABASE_URL in your environment variables

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@image_upload_blueprint.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "You must be logged in to upload images."}), 401

    username = session['username']

    if 'photo' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['photo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "No selected file or file type is not allowed"}), 400

    image_blob = file.read()

    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cur.fetchone()[0]

        filename = secure_filename(file.filename)

        cur.execute(
            "INSERT INTO images (user_id, image_path, image_blob) VALUES (%s, %s, %s)",
            (user_id, filename, image_blob)
        )
        conn.commit()

        return jsonify({"status": "success", "message": "Image successfully uploaded"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": "Failed to upload image: " + str(e)}), 500
    finally:
        cur.close()
        conn.close()

# def fetch_images_from_db():
#     cur = conn.cursor()
#     cur.execute("SELECT image_blob FROM images")
#     rows = cur.fetchall()

#     # Encode image blobs to Base64 strings
#     images = [base64.b64encode(row[0]).decode('utf-8') for row in rows]

#     return images
@image_upload_blueprint.route('/fetch_user_images', methods=['GET'])
def fetch_user_images():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "You must be logged in to fetch images."}), 401

    username = session['username']

    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("SELECT images.id, images.image_path, images.image_blob FROM images INNER JOIN users ON images.user_id = users.id WHERE users.username = %s", (username,))
        images = cur.fetchall()

        # Convert to JSON-friendly format
        image_data = []
        for img in images:
            image_id = img[0]
            image_path = img[1]
            image_blob = base64.b64encode(img[2]).decode('utf-8')  # Encode blob as base64 string
            image_data.append({"id": image_id, "image_path": image_path, "image_blob": image_blob})

        return jsonify({"status": "success", "images": image_data}), 200
    except Exception as e:
        # Log the traceback for detailed error information
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Failed to fetch images: " + str(e)}), 500
    finally:
        if 'cur' in locals() and cur is not None:
            cur.close()
            conn.close()

# Define endpoint to fetch images
# @image_upload_blueprint.route('/fetch_images', methods=['GET'])
# def fetch_users_images():
#     print("Fetching images...")  # Debugging statement
#     try:
#         images = fetch_images_from_db()
#         return jsonify(images)
#     except Exception as e:
#         print(f"Error fetching images: {str(e)}")  # Log the error
#         return jsonify({'error': 'Internal Server Error'}), 500
