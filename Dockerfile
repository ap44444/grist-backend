FROM python:3.12-slim

# 1. Environment setup
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 2. Install Linux-level dependencies (for Database support)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. Upgrade Pip with the "root-ignore" flag
RUN pip install --root-user-action=ignore --upgrade pip

# 4. Install your Python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your project code into the container
COPY . /app/

# 6. Start the server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "grist_project.wsgi:application"]