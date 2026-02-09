FROM python:3.11.4-slim-bookworm

# Set work directory
WORKDIR /usr/src/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Make entrypoint script executable with explicit permissions
RUN chmod 755 /usr/src/app/entrypoint.sh

# Run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]