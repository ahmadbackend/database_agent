from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE VIEW v_sales_detail AS
                SELECT
                    date(i.created_at) AS sale_date,
                    i.number AS invoice_number,
                    b.name AS branch,
                    s.name AS seller,
                    p.name AS product,
                    p.barcode AS barcode,
                    ii.quantity AS quantity,
                    ii.unit_price AS unit_price,
                    (ii.quantity * ii.unit_price) AS line_total
                FROM pharmacy_invoiceitem ii
                JOIN pharmacy_invoice i ON ii.invoice_id = i.id
                JOIN pharmacy_branch b ON i.branch_id = b.id
                JOIN pharmacy_seller s ON i.seller_id = s.id
                JOIN pharmacy_product p ON ii.product_id = p.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS v_sales_detail;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE VIEW v_product_stock AS
                SELECT
                    name AS product,
                    barcode,
                    price,
                    stock,
                    expiry_date
                FROM pharmacy_product;
            """,
            reverse_sql="DROP VIEW IF EXISTS v_product_stock;",
        ),
        migrations.RunSQL(
            sql="""
                CREATE VIEW v_branch_sellers AS
                SELECT
                    b.name AS branch,
                    s.name AS seller,
                    sp.name AS supervisor
                FROM pharmacy_seller s
                JOIN pharmacy_branch b ON s.branch_id = b.id
                LEFT JOIN pharmacy_supervisor sp ON b.supervisor_id = sp.id;
            """,
            reverse_sql="DROP VIEW IF EXISTS v_branch_sellers;",
        ),
    ]
