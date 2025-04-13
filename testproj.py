#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  6 16:30:54 2025
@author: madisonskinner
"""

from flask import current_app
from sqlalchemy import text
import psycopg2
from psycopg2.extras import execute_values


try:
    from Webscraping import Users, Professors, UserProfessors
except ImportError:
    from Webscraping import Users, Professors, UserProfessors  

# Swap Name Order Function
def swap_name_order(name):
    parts = name.strip().split()
    if len(parts) == 2:
        first, last = parts
        return f"{last} {first}"
    return name

# valid to review:
def is_authorized_to_review(user_id, professor_id):
    """
    Checks if a user is authorized to review a given professor
    based on the user_professors table.
    """
    db = current_app.extensions['sqlalchemy']
    enrollment = db.session.query(UserProfessors).filter_by(
        user_id=user_id,
        professor_id=professor_id,
        is_valid=True
    ).first()
    return enrollment is not None

# Enrollment Function 
def enroll_professors(user_id):
    try:
        db = current_app.extensions['sqlalchemy'] # Access the SQLAlchemy instance

        # Read and format professor names
        try:
            with open("professors.txt", "r", encoding="utf-8") as file:
                professor_names = [swap_name_order(line.strip()) for line in file.readlines()]
        except FileNotFoundError:
            print("Error: professors.txt not found.")
            return

        print("Formatted professor names:", professor_names)

        # Fetch professor IDs using SQLAlchemy
        professor_ids = db.session.query(Professors.professor_id).filter(
            db.func.lower(db.func.trim(Professors.name)).in_([name.lower().strip() for name in professor_names])
        ).all()
        professor_ids = [pid[0] for pid in professor_ids]

        if professor_ids:
            for prof_id in professor_ids:
                # Use SQLAlchemy to insert/update user_professors
                existing_enrollment = db.session.query(UserProfessors).filter_by(
                    user_id=user_id,
                    professor_id=prof_id
                ).first()

                if existing_enrollment:
                    existing_enrollment.is_valid = True
                else:
                    new_enrollment = UserProfessors(user_id=user_id, professor_id=prof_id, is_valid=True)
                    db.session.add(new_enrollment)

            db.session.commit()
            print("Professors enrolled successfully.")
        else:
            print("No matching professors found.")
    except Exception as e:
        print(f"Error during enrollment: {e}")

# establish moderators - Use SQLAlchemy models
def moderator(user_id):
    db = current_app.extensions['sqlalchemy']
    user = db.session.query(Users).get(user_id)
    return user and user.moderator

# auto moderation features (these seem fine as they are)
flagged_words = {'fuck', 'fucking', 'bitch', 'shit', 'pussy', 'nigga', 'hell', 'ass'}

def contains_flagged_words(text):
    return any(word in text.lower() for word in flagged_words)

def moderate_review_automatically(review_content):
    if contains_flagged_words(review_content):
        return {'status': 'flagged', 'auto_flagged': True}
    else:
        return {'status': 'approved', 'auto_flagged': False}
