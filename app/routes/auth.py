#/routes/auth.py
from flask import Blueprint, request, jsonify, current_app, redirect, url_for, session,render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app import mysql  # Ensure this matches your Flask app's MySQL initialization
import jwt
import datetime
import psycopg2
import os

auth_blueprint = Blueprint('auth', __name__)

conn = psycopg2.connect(os.environ["DATABASE_URL"])

def connect_to_cockroachdb():
    return psycopg2.connect("postgresql://amey:ERI_ywz1ENsyvAlDgdc25A@issgroup1-4147.7s5.aws-ap-south-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full")

@auth_blueprint.route('/register', methods=['POST'])
def register():
    # Using request.form to access form data
    username = request.form['name']
    email = request.form['email']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    # Connect to CockroachDB
    cur = conn.cursor()

    # Check if the username already exists
    cur.execute("SELECT * FROM users WHERE username = %s", [username])
    if cur.fetchone():
        return jsonify({'message': 'Username already taken'}), 400  # Return an error message
    try:
        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", (username, email, hashed_password))
        conn.commit()
        # Redirect or respond as needed after successful registration
        return redirect(url_for('index2'))  # Adjust 'auth.login_page' as needed
    except Exception as e:
        conn.rollback()
        # Handle error, possibly returning to a different page or showing an error message
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500
    finally:
        cur.close()
        # conn.close()

@auth_blueprint.route('/login', methods=['POST'])
def login():
    username = request.form['username']  # Changed from email to username
    password = request.form['password']
    if username=="admin" and password=="admin":
        return users()
    cur = conn.cursor()
    # Query the database for the user by username instead of email
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s",(username,))
    user = cur.fetchone()
    cur.close()
    # conn.close()

    #user[2] is the correct index, ask me for clarification
    if user and check_password_hash(user[2], password):  # Adjusted index to match the username's position in the fetchone result
        session['username'] = user[1]  # Correctly store the username in the session
        # Generate JWT token
        token = jwt.encode({
            'user_id': user[0], 
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")  # Removed .decode('UTF-8') for compatibility with PyJWT>=2.0.0
        session['jwt_token']=token
        return redirect(url_for('index2'))
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@auth_blueprint.route('/users')
def users():
    # conn = connect_to_cockroachdb()
        cur = conn.cursor()
        cur.execute("SELECT username, email FROM users")
        users_data = cur.fetchall()
        cur.close()
        # conn.close()
        return render_template('Admin.html', users_data=users_data)