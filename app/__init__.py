#/app/__init__.py
from flask import Flask, render_template, session, redirect, url_for
from flask_mysqldb import MySQL
import os
import jwt
import psycopg2
# from app.routes.image_upload import image_upload_blueprint

app = Flask(__name__)

# app.register_blueprint(image_upload_blueprint, url_prefix='/image', name='image_upload')

# app = Flask(__name__)
def connect_to_cockroachdb():
    return psycopg2.connect("postgresql://amey:ERI_ywz1ENsyvAlDgdc25A@issgroup1-4147.7s5.aws-ap-south-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full")
# Application Configuration
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'Agyeya'
# app.config['MYSQL_PASSWORD'] = 'Alcohol4life@'
# app.config['MYSQL_DB'] = 'Project_db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads') #made ti from absolute path to relative path
app.config['SECRET_KEY'] = 'Rasputin'  # Needed for session management

# Initialize MySQL
mysql = MySQL(app)

# Import blueprints
from app.routes.auth import auth_blueprint
from app.routes.image_upload import image_upload_blueprint
from app.routes.music_upload import audio_blueprint  # Import the music upload blueprint
from app.routes.create_video import video_creation_blueprint  # Import the video creation blueprint

# Register blueprints
app.register_blueprint(auth_blueprint, url_prefix='/auth')
app.register_blueprint(image_upload_blueprint, url_prefix='/image')
app.register_blueprint(audio_blueprint, url_prefix='/audio')  # Register the music upload blueprint
app.register_blueprint(video_creation_blueprint, url_prefix='/video')


# Define root route
@app.route('/')
def index():
    jwt_token = None
    if 'jwt_token' in session:
        jwt_token = session.get('jwt_token')
        print(jwt_token)
    
    if jwt_token:
        try:
            data = jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if 'user_id' in data:
                return redirect(url_for('index2'))
        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    
    return redirect(url_for('index'))

# Additional routes for other pages
@app.route('/register')
def register_page():
    jwt_token = session.get('jwt_token')
    if jwt_token:
        try:
            data = jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=["HS256"])
            if 'user_id' in data:
                return redirect(url_for('index2'))
        except jwt.ExpiredSignatureError:
            # Token has expired, clear the session and redirect to login
            session.clear()
            return redirect(url_for('index'))

    return render_template('Register.html')

@app.route('/index2')
def index2():
    jwt_token = None
    if 'jwt_token' in session:
        jwt_token = session.get('jwt_token')
        print(jwt_token)
    else:
        return redirect(url_for('index'))
    if jwt_token:
        data = jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        if 'user_id' not in data:
            return redirect(url_for('index'))
    return render_template('index2.html')

@app.route('/admin')
def admin():
    return render_template('Admin.html')

@app.route('/editing')
def editing_page():
    jwt_token = None
    if 'jwt_token' in session:
        jwt_token = session.get('jwt_token')
        print(jwt_token)
    else:
        return redirect(url_for('index'))
    if jwt_token:
        data = jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        if 'user_id' not in data:
            return redirect(url_for('index'))
    return render_template('Editing-page.html')

@app.route('/success')
def success_page():
    jwt_token = None
    if 'jwt_token' in session:
        jwt_token = session.get('jwt_token')
        print(jwt_token)
    else:
        return redirect(url_for('index'))
    if jwt_token:
        data = jwt.decode(jwt_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        if 'user_id' not in data:
            return redirect(url_for('index'))
    return render_template('successpage.html')

if __name__ == '__main__':
    app.run(debug=True)
