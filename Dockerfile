# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system dependencies for PostgreSQL and building Python packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application code
COPY . /app/

# 7. Collect static files (optional, but good for production)
# RUN python manage.py collectstatic --noinput

# 8. Run the application using Gunicorn
# Replace 'grist_backend' with the name of the folder containing your wsgi.py
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "grist_backend.wsgi:application"]