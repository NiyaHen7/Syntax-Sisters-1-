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
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy.sql import text
import testproj
from selenium.webdriver.chrome.options import Options
import logging


logging.basicConfig(level=logging.INFO)

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


# Hiding the bb login from the user
def get_headless_driver():
    options = Options()
    options.add_argument("--headless=new")  # Ensures a headless browser
    options.add_argument("--disable-gpu")  # Required for headless mode in some environments
    options.add_argument("--window-size=1920x1080")  # Simulate a screen size
    options.add_argument("--no-sandbox")  # Bypass OS security model if necessary
    options.add_argument("--disable-dev-shm-usage")  # Prevent memory overflow issues
    options.add_argument("--log-level=3")  # Suppress unnecessary logs

    driver = webdriver.Chrome(options=options)
    return driver

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
                                
# Create tables explicitly in app contex
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('login.html')

# for the search bar to be functional
# it must render the professors page with a filter
# the filter will be based on the input from the search bar, 
# submitted by the "search function"

# use login as a reference

@app.route('/professors', methods=['GET', 'POST'])
def professors_page():
    try:
        professors = db.session.execute(db.select(Professors)).scalars().all()
        return render_template('professors.html', professors=professors)
    except Exception as e:
        return f"Something isn't working: {str(e)}"

@app.route('/search-professors', methods=['GET', 'POST'])
def search_professors():
    try:
        if request.method == 'POST':
            user_search = request.form.get('user_search', '')
            user_search = user_search.title() # by passes the case sensitivity 
        # access the database and grab the professors
        ##professors = db.session.execute(db.select(Professors)).scalars().all()
        # then send these professors to the front end
            professors = db.session.execute(
                db.select(Professors).where(Professors.name.contains(user_search))
            ).scalars().all()

            filtered_professors = [
                {
                    "professor_id": prof.professor_id,
                    "name": prof.name.title(),  # Optional: format nicely
                    "professor_type": prof.professor_type
                }
                for prof in professors
            ]
    
        return render_template('professors.html', professors=filtered_professors)
    except Exception as e:
        return f"Something isn't working: {str(e)}"
    
@app.route('/professor-profile/<name>')
def professor_profile(name):
    return render_template('professor_profile.html', name=name)

@app.route('/student-profile')
def student_profile():
    try:
        # we do a similar thing for student
        # but we will have to filter by the user name 
        # ( we can filter by the username we recieved from the webscraping)
        student_profile = db.session.execute(db.select(Users)).scalars().all()
        ### i will update this code in a bit
    except Exception as e:
        # we will also need to update this error message
        # to be more cohesive
        return f"Something isn't working: {str(e)}"

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

    driver = get_headless_driver()
    driver.implicitly_wait(10)

    driver.get("https://blackboard.ncat.edu/ultra/course")

    try:
        driver.find_element(By.ID, "user_id").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "entry-login").click()

        WebDriverWait(driver, 180).until(
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
                    new_professor = Professors(name=instructor, professor_type="Unknown")
                    db.session.add(new_professor)
            db.session.commit()
        print("Extracted Instructors:", instructors)

        # Save to a file
        with open("professors.txt", "w", encoding="utf-8") as f:
            for instructor in instructors:
                f.write(f"{instructor}\n")

        print("Extraction complete! Check professors.txt")

        # Get the user_id from the session and call enroll_professors
        user = Users.query.filter_by(username=username).first()
        if user:
            user_id = user.user_id
            testproj.enroll_professors(user_id) #call the function.
        else:
            print("User not found.")

    except Exception as e:
        print(f"Error during scraping: {e}")

    finally:
        driver.quit()

    return render_template('index.html')

if __name__ == '__main__':
    app.run()

