# core/management/commands/import_mongo_data.py
from django.core.management.base import BaseCommand
import sys
import os

# Add the src directory to Python path
sys.path.append('/app/src')


class Command(BaseCommand):
    help = 'Import CSV data into MongoDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--datasets',
            type=str,
            help='Comma-separated list of datasets to import (amazon_categories,amazon_products,fashion)',
            default='all'
        )

    def handle(self, *args, **options):
        try:
            from mongo_Scripts.import_all_data import (
                import_amazon_categories,
                import_amazon_products,
                import_fashion_dataset,
                create_indexes
            )

            datasets = options['datasets']

            if datasets == 'all' or 'amazon_categories' in datasets:
                self.stdout.write("Importing Amazon categories...")
                import_amazon_categories()

            if datasets == 'all' or 'amazon_products' in datasets:
                self.stdout.write("Importing Amazon products...")
                import_amazon_products()

            if datasets == 'all' or 'fashion' in datasets:
                self.stdout.write("Importing fashion dataset...")
                import_fashion_dataset()

            self.stdout.write("Creating indexes...")
            create_indexes()

            self.stdout.write(
                self.style.SUCCESS('Successfully imported all data into MongoDB')
            )

        except Exception as e:
            self.stderr.write(f"Error importing data: {e}")
            raise
