import os
import csv
import datetime
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

# Set up logging
logging.basicConfig(
    filename=os.path.join(settings.BASE_DIR, 'backup.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Command(BaseCommand):
    help = 'Backup MySQL database tables to CSV files'

    def handle(self, *args, **options):
        try:
            # Create backup directory with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(settings.BASE_DIR, 'backup', timestamp)
            os.makedirs(backup_dir, exist_ok=True)
            logging.info(f'Created backup directory: {backup_dir}')

            # Get all tables from the database
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                logging.info(f'Found {len(tables)} tables to backup')

            # Export each table to CSV
            for table in tables:
                if table.startswith('django_') or table.startswith('auth_'):  # Skip Django system tables
                    continue

                csv_file = os.path.join(backup_dir, f'{table}.csv')
                
                try:
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

                    logging.info(f'Successfully backed up {table} to {csv_file}')
                    self.stdout.write(self.style.SUCCESS(f'Successfully backed up {table} to {csv_file}'))

                except Exception as e:
                    logging.error(f'Error backing up table {table}: {str(e)}')
                    self.stdout.write(self.style.ERROR(f'Error backing up table {table}: {str(e)}'))

            # Clean up old backups (keep only last 5)
            backup_root = os.path.join(settings.BASE_DIR, 'backup')
            if os.path.exists(backup_root):
                backups = sorted([d for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))])
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        old_backup_path = os.path.join(backup_root, old_backup)
                        try:
                            import shutil
                            shutil.rmtree(old_backup_path)
                            logging.info(f'Removed old backup: {old_backup_path}')
                        except Exception as e:
                            logging.error(f'Error removing old backup {old_backup_path}: {str(e)}')

            logging.info(f'Backup completed successfully in {backup_dir}')
            self.stdout.write(self.style.SUCCESS(f'Backup completed in {backup_dir}'))

        except Exception as e:
            logging.error(f'Backup failed: {str(e)}')
            self.stdout.write(self.style.ERROR(f'Backup failed: {str(e)}')) 