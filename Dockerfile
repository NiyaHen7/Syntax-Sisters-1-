# Use an official Python image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc python3-dev
RUN apt-get update && apt-get install -y git

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "Webscraping.py"]
