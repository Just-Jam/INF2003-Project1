# python
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Category
import csv
import os

class Command(BaseCommand):
    help = 'Import categories from a CSV into the Category model.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file (e.g. src/datasets/amazon_categories.csv)')
        parser.add_argument('--name-col', type=str, default='category_name', help='CSV column for category name')
        parser.add_argument('--desc-col', type=str, default='description', help='CSV column for description')
        parser.add_argument('--parent-col', type=str, default='parent', help='CSV column for parent category name')
        parser.add_argument('--path-sep', type=str, default='>', help='If parent cell contains a path (A > B > C), this is the separator')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        name_col = options['name_col']
        desc_col = options['desc_col']
        parent_col = options['parent_col']
        path_sep = options['path_sep']

        if not os.path.exists(csv_path):
            raise CommandError(f"CSV not found: {csv_path}")

        created = 0
        updated = 0
        skipped = 0

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if name_col not in reader.fieldnames:
                raise CommandError(f"CSV missing required column: {name_col}")

            with transaction.atomic():
                for row in reader:
                    raw_name = (row.get(name_col) or '').strip()
                    if not raw_name:
                        skipped += 1
                        continue

                    description = (row.get(desc_col) or '').strip()
                    parent_cell = (row.get(parent_col) or '').strip() if parent_col in reader.fieldnames else ''

                    parent_obj = None
                    if parent_cell:
                        # support hierarchical parent path like "Electronics > Computers"
                        if path_sep and path_sep in parent_cell:
                            parts = [p.strip() for p in parent_cell.split(path_sep) if p.strip()]
                            parent_obj = None
                            for part in parts:
                                parent_obj, _ = Category.objects.get_or_create(
                                    category_name=part,
                                    defaults={'description': ''}
                                )
                        else:
                            parent_obj, _ = Category.objects.get_or_create(
                                category_name=parent_cell,
                                defaults={'description': ''}
                            )

                    obj, was_created = Category.objects.update_or_create(
                        category_name=raw_name,
                        defaults={
                            'description': description,
                            'parent_category': parent_obj
                        }
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

        self.stdout.write(self.style.SUCCESS(f'Import finished: created={created}, updated={updated}, skipped={skipped}'))
