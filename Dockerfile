# Use Amazon Linux 2 image with AWS CLI
FROM amazon/aws-cli:2.13.33

# Install Python and pip
RUN yum update -y && \
    yum install -y python3.11 python3.11-pip && \
    yum clean all

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    PORT=8080

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN python3.11 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for SQLite database and uploads
RUN mkdir -p instance && chmod 777 instance && \
    mkdir -p static/uploads && chmod 777 static/uploads

# Expose port
EXPOSE 8080

# Run the application
CMD ["python3.11", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
