# Admin Panel Dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create user and set permissions
RUN useradd -m adminuser && chown -R adminuser:adminuser /app

# Make entrypoint executable
RUN chmod +x entrypoint.sh

ENV PYTHONUNBUFFERED=1

EXPOSE 5001

# Entrypoint runs as root to set permissions, then drops to adminuser
ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--user", "adminuser", "--group", "adminuser", "app:app"]
