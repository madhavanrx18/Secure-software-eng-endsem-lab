FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Install PostgreSQL dependencies
RUN apk add --no-cache postgresql-dev gcc musl-dev

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV DATABASE_URL=postgresql://voting_user:voting_pass@postgres:5432/voting_db

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "app.py"]