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
from flask import jsonify
import time 


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

@app.route('/session_user')
def get_session_user():
    return f"Current session user: {session.get('user', 'No user logged in')}"


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
    professor_type = db.Column(db.String(255), nullable=False)

                                
# Create tables explicitly in app contex
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

# Create tables explicitly in app context

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

from flask import request # Import request

def swap_name_order(name):
    parts = name.strip().split()
    if len(parts) == 2:
        first, last = parts
        return f"{last} {first}"
    return name


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
        search_term = request.args.get('search_term')
        professors = Professors.query.order_by(Professors.name)

        if search_term:
            search_term_lower = search_term.lower()
            professors = professors.filter(Professors.name.ilike(f"%{search_term_lower}%"))

        professors_list = professors.all() # Fetch the results

        # Swap names for display
        formatted_professors = []
        for professor in professors_list:
            formatted_professor = {
                'name': swap_name_order(professor.name),
                'professor_type': professor.professor_type
            }
            formatted_professors.append(formatted_professor)

        return render_template('professors.html', professors=formatted_professors, search_term=search_term)
    except Exception as e:
        return f"Something isn't working: {str(e)}"



@app.route('/student-profile')
def student_profile():
    try:
        # Check if the user is logged in (username is in the session)
        if 'username' in session:
            username = session['username']
            user_profile = Users.query.filter_by(username=username).first()

            if user_profile:
                # Render the student profile template with the user's data
                return render_template('student_profile.html', user=user_profile)
            else:
                return "User profile not found.", 404
        else:
            # If the user is not logged in, redirect them to the login page or display an error
            return "User not logged in.", 401
    except Exception as e:
        return f"Error retrieving student profile: {str(e)}"
    
@app.route('/moderation_page')
def moderation_page():
    print(session)  # Print session contents to debug
    if not session.get('is_moderator'):
        print("Moderator check failed!")  # Debugging
        return "Access Denied", 403  

    reported_reviews = db.session.execute(text("SELECT * FROM reviews WHERE reported = True")).fetchall()
    return render_template('moderation.html', reported_reviews=reported_reviews)

@app.route('/fetch_login', methods=['POST'])
def fetch_login():
    if request.method == 'POST': 
        username = request.form['username']
        password = request.form['password']

        # Check if user already exists
        user = Users.query.filter_by(username=username).first()
        if not user:
            hashed_password = generate_password_hash(password)
            new_user = Users(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            user = new_user #set user to the new user.
    
    # Fix auto-increment sequence
        db.session.execute(text("SELECT setval('users_user_id_seq', (SELECT COALESCE(MAX(user_id), 1) FROM users), true);"))
        db.session.commit()

        # Store username in session instead of passing via URL
        session['username'] = username
        session['password'] = password
        session['user_id'] = user.user_id
        session['is_moderator'] = bool(user.moderator)

    session['username'] = username
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

        # Incremental Scroll Logic with WebDriverWait
        scroll_pause_time = 2  # Adjust as needed
        last_height = driver.execute_script("return document.body.scrollHeight")
        course_elements = driver.find_elements(By.CLASS_NAME, "instructors")  #Initial instructor list.

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

            # Explicitly wait for more instructors to load
            try:
                WebDriverWait(driver, 10).until(
                    lambda driver: len(driver.find_elements(By.CLASS_NAME, "instructors")) > len(course_elements)
                )
            except:
                break #if nothing new is loaded, break.

            course_elements = driver.find_elements(By.CLASS_NAME, "instructors") #update the instructor list.

        instructors = []
        for course in course_elements:
            professor_name = course.text.strip()
            if professor_name and professor_name != 'Multiple Instructors':
                instructors.append(professor_name)

        print("Extracted Instructors:", instructors)

        with app.app_context():
            for instructor in instructors:
                formatted_instructor = swap_name_order(instructor)
                existing_professor = Professors.query.filter_by(name=formatted_instructor).first()
                if not existing_professor:
                    new_professor = Professors(name=formatted_instructor, professor_type="Unknown")
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
            testproj.enroll_professors(user_id)
        else:
            print("User not found.")

    except Exception as e:
        print(f"Error during scraping: {e}")

    finally:
        driver.quit()

    return render_template('index.html')

def swap_name_order(name):
    parts = name.strip().split()
    if len(parts) == 2:
        first, last = parts
        return f"{last} {first}"
    return name

if __name__ == '__main__':
    app.run()
