#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 19:05:46 2025

@author: madisonskinner
"""

import psycopg2
from psycopg2.extras import execute_values

# Function to swap "First Last" → "Last First"
def swap_name_order(name):
    parts = name.strip().split()
    if len(parts) == 2:  # Assuming "First Last"
        first, last = parts
        return f"{last} {first}"  # Convert to "Last First"
    return name  # Return as-is if unexpected format

# Connect to your database
conn = psycopg2.connect(
    dbname="school_reviews",
    user="postgres",
    password="password",
    host="localhost"
)
cur = conn.cursor()

# Get current user ID (replace this with dynamic retrieval in Flask)
user_id = 19  

# Read and format professor names
with open("professors.txt", "r", encoding="utf-8") as file:
    professor_names = [swap_name_order(line.strip()) for line in file.readlines()]

print("Formatted professor names for DB query:", professor_names)  # Debugging line

# Fetch corresponding professor IDs from the database
query = """
    SELECT professor_id FROM professors WHERE TRIM(LOWER(name)) = ANY(%s);
"""
cur.execute(query, ([name.lower().strip() for name in professor_names],))
professor_ids = [row[0] for row in cur.fetchall()]

print("Matched professor IDs:", professor_ids)  # Debugging line

# Insert matched professor IDs into user_professors if any were found
if professor_ids:
    insert_query = """
        INSERT INTO user_professors (user_id, professor_id, is_valid)
        VALUES %s
        ON CONFLICT (user_id, professor_id) DO UPDATE 
        SET is_valid = EXCLUDED.is_valid;
    """
    values = [(user_id, prof_id, True) for prof_id in professor_ids]
    execute_values(cur, insert_query, values)
    conn.commit()  # Ensure changes are saved
    print("Professors successfully inserted into user_professors.")
else:
    print("No matching professor IDs found. Nothing inserted.")

# Fetch and print all records for this user from user_professors
cur.execute("SELECT * FROM user_professors WHERE user_id = %s;", (user_id,))
rows = cur.fetchall()

# Print results
print("User's enrolled professors:")
for row in rows:
    print(row)

# Close the connection
cur.close()
conn.close()
