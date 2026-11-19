from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0002_reporting_views'),
    ]

    operations = [
        # SQLite cannot ALTER a view: drop and recreate with the supervisor column
        migrations.RunSQL(
            sql=[
                "DROP VIEW IF EXISTS v_sales_detail;",
                """
                CREATE VIEW v_sales_detail AS
                SELECT
                    date(i.created_at) AS sale_date,
                    i.number AS invoice_number,
                    b.name AS branch,
                    s.name AS seller,
                    sp.name AS supervisor,
                    p.name AS product,
                    p.barcode AS barcode,
                    ii.quantity AS quantity,
                    ii.unit_price AS unit_price,
                    (ii.quantity * ii.unit_price) AS line_total
                FROM pharmacy_invoiceitem ii
                JOIN pharmacy_invoice i ON ii.invoice_id = i.id
                JOIN pharmacy_branch b ON i.branch_id = b.id
                JOIN pharmacy_seller s ON i.seller_id = s.id
                LEFT JOIN pharmacy_supervisor sp ON b.supervisor_id = sp.id
                JOIN pharmacy_product p ON ii.product_id = p.id;
                """,
            ],
            reverse_sql=[
                "DROP VIEW IF EXISTS v_sales_detail;",
                """
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
            ],
        ),
        migrations.RunSQL(
            sql="""
                CREATE VIEW v_daily_sales AS
                SELECT
                    sale_date,
                    branch,
                    seller,
                    product,
                    SUM(quantity) AS units_sold,
                    ROUND(SUM(line_total), 2) AS revenue,
                    COUNT(DISTINCT invoice_number) AS invoices
                FROM v_sales_detail
                GROUP BY sale_date, branch, seller, product;
            """,
            reverse_sql="DROP VIEW IF EXISTS v_daily_sales;",
        ),
    ]
