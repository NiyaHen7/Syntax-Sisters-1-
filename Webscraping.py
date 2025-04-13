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
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy.sql import text
from selenium.webdriver.chrome.options import Options
import logging
import time
import threading
import testproj

logging.basicConfig(level=logging.INFO)

load_dotenv()  # Load environment variables from .env

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Loaded DATABASE_URL: {DATABASE_URL}")  # Debugging check

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)  # Secure sessions

# Configure the PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL',
                                           'postgresql://postgres:password@localhost/school_reviews')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

scraping_status = {}

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
    moderator = db.Column(db.Boolean, default=False)
    reviews = db.relationship('Reviews', back_populates='user')
    user_professors = db.relationship('UserProfessors', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Professors(db.Model):
    __tablename__ = 'professors'
    professor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    professor_type = db.Column(db.String(255), nullable=False)

    reviews = db.relationship('Reviews', back_populates='professor')
    user_professors = db.relationship('UserProfessors', back_populates='professor')  #


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


class UserProfessors(db.Model):
    __tablename__ = 'user_professors'
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey('professors.professor_id'), primary_key=True)
    is_valid = db.Column(db.Boolean, default=True)

    user = db.relationship('Users', back_populates='user_professors')
    professor = db.relationship('Professors', back_populates='user_professors')


# Create tables explicitly in app context

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/home')
def home():
    return render_template('index.html')


@app.route('/loading')
def loading():
    return render_template('loading.html')


@app.route('/professors', methods=['GET', 'POST'])
def professors_page():
    try:
        search_term = request.args.get('search_term')
        professors = Professors.query.filter(Professors.professor_type != 'Unknown').order_by(Professors.name) # Exclude 'Unknown'

        if search_term:
            search_term = search_term.lower()
            professors = professors.filter(Professors.name.ilike(f"%{search_term}%"))

        professors_list = professors.all()

        formatted_professors = []
        for professor in professors_list:
            formatted_professor = {
                'name': swap_name_order(professor.name),
                'professor_type': professor.professor_type,
                'professor_id': professor.professor_id
            }
            formatted_professors.append(formatted_professor)

        return render_template('professors.html', professors=formatted_professors, search_term=search_term)
    except Exception as e:
        return f"Something isn't working: {str(e)}"


@app.route('/student-profile')
def student_profile():
    try:
        if 'username' in session:
            username = session['username']
            user = Users.query.filter_by(username=username).first()

            if user:
                # Fetch reviews associated with the user, ordered by creation date
                user_reviews = Reviews.query.filter_by(user_id=user.user_id).order_by(Reviews.created_at.desc()).all()

                # Log the number of reviews fetched
                logging.info(f"Fetched {len(user_reviews)} reviews for user: {username}")

                return render_template('student_profile.html', user=user, user_reviews=user_reviews)
            else:
                return "User profile not found.", 404
        else:
            return "User not logged in.", 401
    except Exception as e:
        logging.error(f"Error retrieving student profile: {str(e)}")
        return f"Error retrieving student profile: {str(e)}"

@app.route('/moderation_page')
def moderation_page():
    print(session)
    if not session.get('is_moderator'):
        print("Moderator check failed!")
        return "Access Denied", 403

    reported_reviews = Reviews.query.filter_by(reported=True).all()
    return render_template('moderation.html', reviews=reported_reviews)


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
            user = new_user  # set user to the new user.
        # Fix auto-increment sequence
        db.session.execute(
            text("SELECT setval('users_user_id_seq', (SELECT COALESCE(MAX(user_id), 1) FROM users), true);"))
        db.session.commit()

        # Store username in session
        session['username'] = username
        session['password'] = password
        session['user_id'] = user.user_id
        session['is_moderator'] = bool(user.moderator)

        logging.info(f"User '{username}' logged in. Redirecting to handle_data.")
        return redirect(url_for("handle_data"))

    return redirect(url_for("login")) # Fallback in case of GET request


@app.route('/handle_data', methods=['GET', 'POST'])
def handle_data():
    username = session.get('username')
    password = session.get('password')

    logging.info(f"'/handle_data' route accessed for user: {username}")

    if not username or not password:
        logging.warning("'/handle_data' - Invalid session (username or password missing).")
        return "Invalid session. Please log in again.", 403

    scraping_status[username] = 'in_progress'
    logging.info(f"'/handle_data' - Scraping status set to 'in_progress' for user: {username}")

    def do_scraping():
        driver = get_headless_driver()
        driver.implicitly_wait(10)
        try:
            logging.info(f"Attempting login for user: {username} in do_scraping")
            driver.get("https://blackboard.ncat.edu/ultra/course")
            driver.find_element(By.ID, "user_id").send_keys(username)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.ID, "entry-login").click()
            logging.info(f"Login successful (hopefully) for user: {username} in do_scraping")

            WebDriverWait(driver, 180).until(
                EC.presence_of_element_located((By.CLASS_NAME, "instructors"))
            )
            logging.info(f"Instructors element found for user: {username} in do_scraping")

            scroll_pause_time = 2
            last_height = driver.execute_script("return document.body.scrollHeight")
            course_elements = driver.find_elements(By.CLASS_NAME, "instructors")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: len(d.find_elements(By.CLASS_NAME, "instructors")) > len(course_elements)
                    )
                except:
                    break

            course_elements = driver.find_elements(By.CLASS_NAME, "instructors")
            instructors = [c.text.strip() for c in course_elements if c.text.strip() and c.text.strip() != 'Multiple Instructors']

            with app.app_context():
                for instructor in instructors:
                    formatted = swap_name_order(instructor)
                    if not Professors.query.filter_by(name=formatted).first():
                        db.session.add(Professors(name=formatted, professor_type="Unknown"))
                db.session.commit()
                logging.info(f"Professors added to database by user: {username} in do_scraping")

                user = Users.query.filter_by(username=username).first()
                if user:
                    testproj.enroll_professors(user.user_id)
                    logging.info(f"'enroll_professors' completed for user: {username} in do_scraping")

            with open("professors.txt", "w", encoding="utf-8") as f:
                for i in instructors:
                    f.write(f"{i}\n")
            logging.info(f"'professors.txt' written for user: {username} in do_scraping")

            scraping_status[username] = 'done'
            logging.info(f"'do_scraping' completed for user: {username}. Status set to 'done'.")

        except Exception as e:
            scraping_status[username] = f"error: {str(e)}"
            logging.error(f"Error during scraping for user {username} in do_scraping: {str(e)}")
        finally:
            driver.quit()
            logging.info(f"Driver quit for user {username} in do_scraping")

    threading.Thread(target=do_scraping).start()

    logging.info(f"'/handle_data' - Redirecting user '{username}' to '/loading'.")
    return redirect(url_for("loading"))

# Polling route to check scraping status
@app.route('/check_scrape_status')
def check_scrape_status():
    username = session.get('username')
    status = scraping_status.get(username, 'idle')
    logging.info(f"'/check_scrape_status' polled by user: {username}. Current status: {status}")
    if status == 'done':
        logging.info(f"'/check_scrape_status' - Scraping done for user: {username}. Redirecting to '/home'.")
        return jsonify({'status': 'done', 'redirect': url_for('home')})
    elif status.startswith('error'):
        logging.error(f"'/check_scrape_status' - Error status for user: {username}: {status}. Consider redirecting to an error page.")
        return jsonify({'status': status, 'redirect': url_for('home')}) # Or an error page
    else:
        return jsonify({'status': status})

# when on the student profile page
# filter the reviews
@app.route('/review', methods=["POST"])
def review():
    stars = request.form.get('stars')
    comment = request.form.get('comment')
    user_id = session['user_id']
    professor_name = request.form.get('prof_name')
    professor_id = request.form.get('prof_id')
    class_format = request.form.get('class_format')
    logging.info(f"/review - Attempting review by User ID: {user_id} for Professor ID: {professor_id}")
    logging.info(f"/review - Session user_id: {session.get('user_id')}")
    logging.info(f"/review - Form prof_id: {professor_id}")
    logging.info(f"/review - Form class_format: {class_format}")

    if not stars or not comment:
        logging.warning("/review - Missing rating or comment.")
        flash("Please provide both a rating and a comment.", "error")  # Use flash for error message
        return redirect(url_for("professor_profile", professor_id=professor_id, name=professor_name))

    is_authorized = testproj.is_authorized_to_review(user_id, professor_id)
    logging.info(f"/review - Authorization check result: {is_authorized}")

    if not is_authorized:
        logging.warning(f"/review - User {user_id} is NOT authorized to review professor {professor_id}.")
        flash("You are not authorized to review this professor.", "error")  # Use flash
        return redirect(url_for("professor_profile", professor_id=professor_id, name=professor_name))

    # Automoderation check
    moderation_result = testproj.moderate_review_automatically(comment)
    if moderation_result['status'] == 'flagged':
        logging.warning(f"/review - Review from User {user_id} was flagged for moderation.")
        flash("Your review contains inappropriate language and cannot be submitted.", "error")  # Use flash
        return redirect(url_for("professor_profile", professor_id=professor_id, name=professor_name))

    new_review = Reviews(
        sql_score=int(stars),
        review=comment,
        user_id=user_id,
        professor_id=professor_id,
        created_at=db.func.now(),
        status='pending',  # Set to 'pending' initially
        auto_flagged=moderation_result['auto_flagged'],
        class_format=class_format
    )
    try:
        db.session.add(new_review)
        db.session.commit()
        logging.info(f"/review - Review submitted by user {user_id} for professor {professor_id} ({professor_name}).")
        return redirect(url_for("professor_profile", name=professor_name, professor_id=professor_id))
    except Exception as e:
        logging.error(f"/review - Error submitting review: {e}")
        flash(f"Error submitting review: {str(e)}", "error")  # Use flash
        return redirect(url_for("professor_profile", professor_id=professor_id, name=professor_name))


@app.route('/professor-profile/<professor_id>/<name>', methods=["GET"])
def professor_profile(professor_id, name):
    user_id = session.get('user_id')
    is_review_allowed = False
    if user_id:
        is_review_allowed = testproj.is_authorized_to_review(user_id, int(professor_id))
    logging.info(f"/professor-profile - User ID: {user_id}, Professor ID: {professor_id}, Review Allowed: {is_review_allowed}")
    reviews = Reviews.query.filter_by(professor_id=professor_id).order_by(
        Reviews.created_at.desc()).all()
    return render_template("professor_profile.html", professor_id=professor_id, name=name, reviews=reviews, is_review_allowed=is_review_allowed)

def swap_name_order(name):
    parts = name.strip().split()
    if len(parts) == 2:
        first, last = parts
        return f"{last} {first}"
    return name

@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    try:
        review = Reviews.query.get(review_id)
        if review:
            if session['user_id'] == review.user_id or session.get('is_moderator'):
                db.session.delete(review)
                db.session.commit()
                logging.info(f"Review {review_id} deleted.")
                flash("Review deleted successfully.", "success")
            else:
                logging.warning(f"User {session['user_id']} tried to delete review {review_id} without authorization.")
                flash("You are not authorized to delete this review.", "error")
        else:
            logging.error(f"Review {review_id} not found for deletion.")
            flash("Review not found.", "error")
    except Exception as e:
        logging.error(f"Error deleting review {review_id}: {str(e)}")
        flash(f"Error deleting review: {str(e)}", "error")
    return redirect(request.referrer)  # Redirect back to the previous page

@app.route('/report_review/<int:review_id>', methods=['POST'])
def report_review(review_id):
    try:
        review = Reviews.query.get(review_id)
        if review:
            review.reported = True
            db.session.commit()
            logging.info(f"Review {review_id} reported.")
            flash("Review reported.", "success")
        else:
            logging.error(f"Review {review_id} not found for reporting.")
            flash("Review not found.", "error")
    except Exception as e:
        logging.error(f"Error reporting review {review_id}: {str(e)}")
        flash(f"Error reporting review: {str(e)}", "error")
    return redirect(request.referrer)  # Redirect back to the previous page

@app.route('/dismiss_review/<int:review_id>', methods=['POST'])
def dismiss_review(review_id):
    try:
        review = Reviews.query.get(review_id)
        if review:
            review.reported = False
            db.session.commit()
            logging.info(f"Review {review_id} dismissed (reported=False).")
            flash("Review dismissed.", "success")
        else:
            logging.error(f"Review {review_id} not found for dismissing.")
            flash("Review not found.", "error")
    except Exception as e:
        logging.error(f"Error dismissing review {review_id}: {str(e)}")
        flash(f"Error dismissing review: {str(e)}", "error")
    return redirect(request.referrer)

if __name__ == '__main__':
    app.run(debug=True)
