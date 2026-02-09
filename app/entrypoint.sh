#!/bin/sh

echo "Starting Patient Monitoring System..."

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Apply database migrations
echo "Creating migrations..."
python manage.py makemigrations core

echo "Applying database migrations..."
python manage.py migrate

echo "Migrations completed successfully!"

# Create superuser if it doesn't exist
echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth.models import User
from core.models import UserProfile
import sys

try:
    if not User.objects.filter(username='admin').exists():
        user = User.objects.create_superuser('admin', 'admin@pms.local', 'admin123')
        UserProfile.objects.create(
            user=user,
            role='admin',
            department='System Administration',
            license_number='ADMIN001'
        )
        print('Superuser created: admin/admin123')
    else:
        print('Superuser already exists')
except Exception as e:
    print(f'Error creating superuser: {e}')
    sys.exit(1)
"

echo "Patient Monitoring System is ready!"
exec "$@"