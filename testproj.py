#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 16:30:54 2025

@author: madisonskinner
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/school_reviews")
RAILWAY_DB_URL = os.getenv("RAILWAY_DB_URL", "postgresql://postgres:wrocDJvJZYmYShWtBHVFgGemQxKjgtvu@switchyard.proxy.rlwy.net:24131/railway")

engine = create_engine(DATABASE_URL)

# Connect to your database
conn = psycopg2.connect(
    dbname="railway",
    user="postgres",
    password="wrocDJvJZYmYShWtBHVFgGemQxKjgtvu",
    host="switchyard.proxy.rlwy.net",
    port="24131"
)
cur = conn.cursor()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure the PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

@app.route('/session_user')
def get_session_user():
    return f"Current session user: {session.get('user', 'No user logged in')}"

# Define Database Models (same as your provided code)
class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    moderator = db.Column(db.Boolean, default=False)  # Ensure this line exists
    reviews = db.relationship('Reviews', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Professors(db.Model):
    __tablename__ = 'professors'
    professor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    professor_type = db.Column(db.String(255), nullable=False, default="Unknown")
    reviews = db.relationship('Reviews', back_populates='professor')

class Reviews(db.Model):
    __tablename__ = 'reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.professor_id'), nullable=False)
    review = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    class_format = db.Column(db.String(255), nullable=True)
    sql_score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    auto_flagged = db.Column(db.Boolean, default=False, nullable=False)
    reported = db.Column(db.Boolean, default=False)

    user = db.relationship('Users', back_populates='reviews')
    professor = db.relationship('Professors', back_populates='reviews')

# Create tables explicitly
with app.app_context():
    db.create_all()

# Swap Name Order Function 
def swap_name_order(name):
    parts = name.strip().split()
    if len(parts) == 2:
        first, last = parts
        return f"{last} {first}"
    return name

# Enrollment Function 
def enroll_professors(user_id):
    try:
        conn = psycopg2.connect(RAILWAY_DB_URL)
        cur = conn.cursor()

        # Read and format professor names
        try:
            with open("professors.txt", "r", encoding="utf-8") as file:
                professor_names = [swap_name_order(line.strip()) for line in file.readlines()]
        except FileNotFoundError:
            print("Error: professors.txt not found.")
            return

        print("Formatted professor names:", professor_names)

        # Fetch professor IDs
        query = """
            SELECT professor_id FROM professors WHERE TRIM(LOWER(name)) = ANY(%s);
        """
        cur.execute(query, ([name.lower().strip() for name in professor_names],))
        professor_ids = [row[0] for row in cur.fetchall()]

        if professor_ids:
            insert_query = """
                INSERT INTO user_professors (user_id, professor_id, is_valid)
                VALUES %s
                ON CONFLICT (user_id, professor_id) DO UPDATE 
                SET is_valid = EXCLUDED.is_valid;
            """
            values = [(user_id, prof_id, True) for prof_id in professor_ids]
            execute_values(cur, insert_query, values)
            conn.commit()
            print("Professors enrolled successfully.")
        else:
            print("No matching professors found.")
    finally:
        cur.close()
        conn.close()

# establish moderators
def moderator(user_id):
    user = Users.query.get(user_id)
    return user and user.moderator  # Checks if the user exists and is a moderator

# auto moderation features
flagged_words = {'fuck', 'fucking', 'bitch', 'shit', 'pussy', 'nigga', 'hell'}

def contains_flagged_words(text):
    return any(word in text.lower() for word in flagged_words)

def moderate_review_automatically(review_content):
    if contains_flagged_words(review_content):
        return {'status': 'flagged', 'auto_flagged': True}
    else:
        return {'status': 'approved', 'auto_flagged': False}

# Routes
@app.route('/')
def index():
    professors = Professors.query.all()
    user_id = session.get('user_id') 
    is_moderator = session.get('is_moderator', False)  # Get moderator status from session
    print("Session User ID:", user_id, "| Is Moderator:", is_moderator)  

    return render_template('index.html', professors=professors, user_id=user_id, is_moderator=is_moderator)

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    if Users.query.filter_by(username=username).first():
        return "Username already exists!", 400

    new_user = Users(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = db.session.execute(text("SELECT * FROM users WHERE username = :u"), {'u': username}).fetchone()

    if user and check_password_hash(user.password_hash, password):  # Ensure password check is correct
        session.clear()
        session['user_id'] = user.user_id
        session['username'] = user.username
        session['is_moderator'] = bool(user.moderator)  # Ensure is_moderator is retrieved

        print(f"Session after login: {session}")  # Debugging
        session.permanent = True
        return redirect(url_for('index'))
    else:
        return "Invalid credentials", 401

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# Enrollment Route
@app.route('/enroll', methods=['POST'])
def run_enrollment():
    if 'user_id' not in session:
        return "Unauthorized", 401

    user_id = session['user_id']
    enroll_professors(user_id)
    return "Enrollment completed."

# Delete Review Route 
@app.route('/delete_review/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    review = Reviews.query.get(review_id)
    if not review:
        return jsonify({'error': 'Review not found'}), 404

    # Check if user is a moderator or the review owner
    if moderator(user_id) or review.user_id == user_id:
        db.session.delete(review)
        db.session.commit()
        return jsonify({'message': 'Review deleted successfully'})
    else:
        return jsonify({'error': 'Permission denied'}), 403

# getting user_id
@app.route('/get_user_id')
def get_user_id():
    if 'username' in session:  # Ensure a user is logged in
        username = session['username']

        # Query database for the user's ID
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_id = cur.fetchone()

        if user_id:
            return f"User ID: {user_id[0]}"
        else:
            return "User not found", 404
    else:
        return "No user logged in", 403

# Moderation Route
@app.route('/submit_review', methods=['POST'])
def submit_review():
    user_id = session.get('user_id')
    print("Session User ID:", session.get('user_id'))

    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    review_content = data.get('content', '')

    moderation_result = moderate_review_automatically(review_content)

    review = Reviews(
        content=review_content,
        status=moderation_result['status'],
        auto_flagged=moderation_result['auto_flagged']
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({'message': 'Review submitted', 'status': moderation_result['status']})

# Report Review
@app.route('/report/<int:review_id>', methods=['POST'])
def report_review(review_id):
    review = Reviews.query.get_or_404(review_id)
    review.reported = True
    db.session.commit()
    return jsonify({'message': 'Review reported successfully'}), 200

# check session 
@app.route('/check_session')
def check_session():
    return f"Session: {session}"

# to Mod Page
@app.route('/moderation_page')
def moderation_page():
    print(f"Session at Moderation Page: {session}")  # Debugging
    if not session.get('is_moderator'):
        print("Moderator check failed!")  # Debugging
        return "Access Denied", 403  

    reported_reviews = db.session.execute(text("SELECT * FROM reviews WHERE reported = True")).fetchall()
    return render_template('moderation.html', reported_reviews=reported_reviews)

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = Users.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)
