#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 8 17:30:59 2025

@author: madisonskinner
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
import time, subprocess, os

app = Flask(__name__, template_folder="templates")

# Configure the PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/school_reviews'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Professor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# Ensure tables exist
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/fetch_login', methods=['POST'])
def fetch_login():
    if request.method == 'POST': 
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        
        # Store user credentials securely
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            new_user = User(username=username, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
        
    return redirect(url_for("handle_data", username=username, password=password))

@app.route('/handle_data/<username>/<password>', methods=['GET', 'POST'])
def handle_data(username=None, password=None):
    driver = webdriver.Chrome()
    driver.get("https://blackboard.ncat.edu/ultra/course")
    time.sleep(3)
    
    driver.find_element(By.ID, "user_id").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "entry-login").click()
    
    time.sleep(15)
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "instructors"))
        )
    except:
        print("Instructor section not found.")
        driver.quit()
        return "Failed to retrieve instructors."

    instructors = []
    course_elements = driver.find_elements(By.CLASS_NAME, "instructors")

    for course in course_elements:
        professor_name = course.text.strip()
        if professor_name and professor_name != 'Multiple Instructors':
            instructors.append(professor_name)
    
    print("Extracted Instructors:", instructors)
    
    with app.app_context():
        for instructor in instructors:
            existing_professor = Professor.query.filter_by(name=instructor).first()
            if not existing_professor:
                new_professor = Professor(name=instructor)
                db.session.add(new_professor)
        db.session.commit()
    
    print("Professor data stored successfully!")
    driver.quit()
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run()
