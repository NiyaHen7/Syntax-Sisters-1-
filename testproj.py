#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 16:30:54 2025

@author: madisonskinner
"""

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure session key

# Configure the PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/school_reviews'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# Define Database Models
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        """Hash password before storing"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password during login"""
        return check_password_hash(self.password_hash, password)

class Professors(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Reviews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professor.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)

# Create tables explicitly in app context (only run once on startup)
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    professors = Professor.query.all()
    return render_template('index.html', professors=professors)

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return "Email already exists!", 400

    new_user = User(name=name, email=email)
    new_user.set_password(password)  # Hash password before storing
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        session['user_id'] = user.id  # Store user session
        return redirect(url_for('index'))
    else:
        return "Invalid credentials!", 403

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/add_professor', methods=['POST'])
def add_professor():
    name = request.form['name']
    new_professor = Professor(name=name)
    db.session.add(new_professor)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_review', methods=['POST'])
def add_review():
    user_id = session.get('user_id')
    if not user_id:
        return "Unauthorized", 403

    professor_id = request.form['professor_id']
    rating = request.form['rating']
    comment = request.form.get('comment', '')

    new_review = Review(user_id=user_id, professor_id=professor_id, rating=rating, comment=comment)
    db.session.add(new_review)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
