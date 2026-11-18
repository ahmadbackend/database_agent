import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from pharmacy.models import (
    Branch, Invoice, InvoiceItem, Product, Seller, Supervisor,
)

DEFAULT_CSV = Path(__file__).resolve().parents[2] / 'data' / 'dummy_data.csv'


class Command(BaseCommand):
    help = 'Load dummy pharmacy data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            default=str(DEFAULT_CSV),
            help='Path to the CSV file (default: pharmacy/data/dummy_data.csv)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options['csv'])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f'File not found: {csv_path}'))
            return

        with csv_path.open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            supervisor, _ = Supervisor.objects.get_or_create(
                name=row['supervisor_name'],
                defaults={
                    'phone': row['supervisor_phone'],
                    'email': row['supervisor_email'],
                },
            )
            branch, _ = Branch.objects.get_or_create(
                name=row['branch_name'],
                defaults={
                    'address': row['branch_address'],
                    'phone': row['branch_phone'],
                    'supervisor': supervisor,
                },
            )
            seller, _ = Seller.objects.get_or_create(
                name=row['seller_name'],
                branch=branch,
                defaults={'phone': row['seller_phone']},
            )
            product, _ = Product.objects.get_or_create(
                barcode=row['barcode'],
                defaults={
                    'name': row['product_name'],
                    'price': row['price'],
                    'expiry_date': row['expiry_date'] or None,
                    'stock': row['stock'] or 0,
                },
            )
            invoice, _ = Invoice.objects.get_or_create(
                number=row['invoice_number'],
                defaults={'branch': branch, 'seller': seller},
            )
            InvoiceItem.objects.get_or_create(
                invoice=invoice,
                product=product,
                defaults={
                    'quantity': row['quantity'],
                    'unit_price': row['unit_price'],
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {len(rows)} rows from {csv_path}'
        ))
