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
import time, subprocess

app = Flask(__name__,template_folder="templates")
# this may need to be changed
node_script = '/Users/owner/Syntax-Sisters-1--1/app.js'

# GET is to requeset data from a resource
# POST is to send data/update

# this renders the login page when the python function is ran
@app.route('/')
def index():
    return render_template('homepage.html')

# from here we recieve the login from the form with 
# the method "POST"
@app.route('/fetch_login', methods=['POST'])
def fetch_login():
    if request.method == 'POST': 
        user_name = request.form['username']
        user_password = request.form['password']
    
    # we then store the information and send it to
    # the handle data function where the existing 
    # web scraping function exists
    return redirect(url_for("handle_data", username=user_name, password=user_password))

# the methods GET & POST allows this function to send & recieve information
@app.route('/handle_data/<username>/<password>', methods=['GET', 'POST'])
def handle_data(username=None, password=None):
    driver = webdriver.Chrome() # Ensure you have the correct ChromeDriver
    driver.get("https://blackboard.ncat.edu/ultra/course")
    # Wait for page to load
    time.sleep(3)
    # Find and fill in the username and password fields
    driver.find_element(By.ID, "user_id").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "entry-login").click()
    # Wait for login to complete

    body = driver.find_element(By.XPATH, "//*[@id='main-content-inner']")
    body.send_keys(Keys.PAGE_DOWN)  # Scrolls down one page
    body.send_keys(Keys.END)  # Scrolls to the bottom

    time.sleep(15)
    # Wait for instructors section to appear
    try:
        WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "instructors"))
    )
    except:
        print("Instructor section not found.")
        driver.quit()
        exit()
    # Scrape instructor names
    instructors = []
    course_elements = driver.find_elements(By.CLASS_NAME, "instructors")

    for course in course_elements:
        try:
            professor_name = course.text
            if professor_name == 'Multiple Instructors':
                pass
            instructors.append(professor_name)
        except:
            print("Error extracting instructor name.")
            continue # Skip if no professor name found

    # Save to a file
    print("Extracted Instructors:", instructors)

    # Save to a file
    with open("professors.txt", "w", encoding="utf-8") as f:  # Added encoding for safety
        for instructor in instructors:
            if instructor:  # Ensure it's not None
                f.write(str(instructor) + "\n")
    # Correct newline
    print("Extraction complete! Check professors.txt")

    driver.quit()
    #start page with professors to view and student profile
    subprocess.Popen(['node', node_script])
    return render_template('index.html')

if __name__ == '__main__':
    app.run()
