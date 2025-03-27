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
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:wrocDJvJZYmYShWtBHVFgGemQxKjgtvu@switchyard.proxy.rlwy.net:24131/railway")

engine = create_engine(DATABASE_URL)

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
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    reviews = db.relationship('Reviews', back_populates='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Professors(db.Model):
    __tablename__ = 'professors'
    professor_id = db.Column(db.Integer, primary_key=True)  # Matches PostgreSQL
    name = db.Column(db.String(255), nullable=False)
    professor_type = db.Column(db.String(255), nullable=False, default="Unknown")  # Matches DB
    reviews = db.relationship('Reviews', back_populates='professor')

class Reviews(db.Model):
    __tablename__ = 'reviews'
    review_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)  # Matches DB
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.professor_id'), nullable=False)  # Matches DB
    review = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    class_format = db.Column(db.String(255), nullable=True)
    sql_score = db.Column(db.Integer, nullable=True)

    user = db.relationship('Users', back_populates='reviews')
    professor = db.relationship('Professors', back_populates='reviews')

# Create tables explicitly in app context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    professors = Professors.query.all()
    return render_template('index.html', professors=professors)

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    username = request.form['username']
    password = request.form['password']

    existing_user = Users.query.filter_by(username=username).first()
    if existing_user:
        return "Username already exists!", 400

    new_user = Users(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = Users.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['user_id'] = user.user_id
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
    
    users = Users.query.get(session['user_id'])
    return render_template('dashboard.html', users=users)

@app.route('/add_professor', methods=['POST'])
def add_professor():
    name = request.form['name']
    new_professor = Professors(name=name)
    db.session.add(new_professor)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_review', methods=['POST'])
def add_review():
    user_id = request.form['user_id']
    professor_id = request.form['professor_id']
    review_text = request.form['review']
    class_format = request.form.get('class_format', None)
    sql_score = request.form.get('sql_score', None)
    
    sql_score = int(sql_score) if sql_score else None
    
    new_review = Reviews(
        user_id=user_id, 
        professor_id=professor_id, 
        review=review_text, 
        class_format=class_format, 
        sql_score=sql_score
    )
    
    db.session.add(new_review)
    db.session.commit()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
