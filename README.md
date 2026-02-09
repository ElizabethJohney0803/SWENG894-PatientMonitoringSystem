# Patient Monitoring System - Quick Start

## Getting Started

1. **Build and start the containers:**
   ```bash
   docker-compose up -d --build
   ```

2. **Access the Django Admin:**
   - URL: http://localhost:8000/admin/
   - Username: `admin`
   - Password: `admin123`

3. **View logs:**
   ```bash
   docker-compose logs -f web
   ```

4. **Stop the system:**
   ```bash
   docker-compose down
   ```

## Default Admin User

The system automatically creates a superuser with these credentials:
- **Username:** admin
- **Password:** admin123
- **Role:** System Administrator

You can change these credentials after logging in.

## Services

- **Web Application:** Django running on port 8000
- **Database:** PostgreSQL running on port 5432
- **Admin Interface:** Available at root URL (redirects to /admin/)


## Development

- Code changes in `./app/` are automatically reloaded
- Database data persists in Docker volume `postgres_data`
- To reset everything: `docker-compose down -v` (removes volumes)