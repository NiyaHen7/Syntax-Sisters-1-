#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 8 17:30:59 2025

@author: madisonskinner
"""


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
import time
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy.sql import text


load_dotenv()  # Load environment variables from .env

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Loaded DATABASE_URL: {DATABASE_URL}")  # Debugging check

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)  # Secure sessions

# Configure the PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost/school_reviews')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define Database Models
class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Professors(db.Model):
    __tablename__ = 'professors'
    professor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    professor_type = db.Column(db.String(255), nullable=False)
                                
# Create tables explicitly in app context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/fetch_login', methods=['POST'])
def fetch_login():
    if request.method == 'POST': 
        username = request.form['username']
        password = request.form['password']

        # Check if user already exists
        existing_user = Users.query.filter_by(username=username).first()
        if not existing_user:
            hashed_password = generate_password_hash(password)
            new_user = Users(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()

    # Fix auto-increment sequence
        db.session.execute(text("SELECT setval('users_user_id_seq', (SELECT COALESCE(MAX(user_id), 1) FROM users), true);"))
        db.session.commit()

        # Store username in session instead of passing via URL
        session['username'] = username
        session['password'] = password  # Not recommended for production!

    return redirect(url_for("handle_data"))

@app.route('/handle_data', methods=['GET', 'POST'])
def handle_data():
    username = session.get('username')
    password = session.get('password')

    if not username or not password:
        return "Invalid session. Please log in again.", 403

    driver = webdriver.Chrome()
    driver.implicitly_wait(10)  # Replaces time.sleep()

    driver.get("https://blackboard.ncat.edu/ultra/course")

    try:
        driver.find_element(By.ID, "user_id").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "entry-login").click()

        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "instructors"))
        )

        instructors = []
        course_elements = driver.find_elements(By.CLASS_NAME, "instructors")

        for course in course_elements:
            professor_name = course.text.strip()
            if professor_name and professor_name != 'Multiple Instructors':
                instructors.append(professor_name)

        print("Extracted Instructors:", instructors)

        with app.app_context():
            for instructor in instructors:
                existing_professor = Professors.query.filter_by(name=instructor).first()
                if not existing_professor:
                    new_professor = Professors(name=instructor, professor_type="Unknown")  # Adjust based on actual schema
                    db.session.add(new_professor)
            db.session.commit()

        print("Professor data stored successfully!")
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()




    return render_template('index.html')

if __name__ == '__main__':
    app.run()

