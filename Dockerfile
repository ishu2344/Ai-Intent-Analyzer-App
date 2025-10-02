# Start from the official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application code into the container
COPY . .

# Expose the port the app runs on (matching your app.py)
EXPOSE 8082

# Define the command to run the application using gunicorn
# Gunicorn is a production-ready WSGI server needed for performance and stability
CMD exec gunicorn --bind :8082 --workers 2 app:app
