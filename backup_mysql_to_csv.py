import os
import csv
import datetime
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = 'Backup MySQL database tables to CSV files'

    def handle(self, *args, **options):
        # Create backup directory with timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(settings.BASE_DIR, 'backup', timestamp)
        os.makedirs(backup_dir, exist_ok=True)

        # Get all tables from the database
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]

        # Export each table to CSV
        for table in tables:
            if table.startswith('django_') or table.startswith('auth_'):  # Skip Django system tables
                continue

            csv_file = os.path.join(backup_dir, f'{table}.csv')
            
            with connection.cursor() as cursor:
                # Get column names
                cursor.execute(f"SHOW COLUMNS FROM {table}")
                columns = [column[0] for column in cursor.fetchall()]
                
                # Get data
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()

            # Write to CSV
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)

            self.stdout.write(self.style.SUCCESS(f'Successfully backed up {table} to {csv_file}'))

        self.stdout.write(self.style.SUCCESS(f'Backup completed in {backup_dir}')) 