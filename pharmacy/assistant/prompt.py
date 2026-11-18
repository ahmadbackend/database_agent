from datetime import date

SCHEMA = """You are a SQLite query generator for a pharmacy group's reporting database.
You can ONLY use the three views below. Raw tables do not exist for you.

VIEW v_sales_detail(sale_date TEXT 'YYYY-MM-DD', invoice_number TEXT, branch TEXT, seller TEXT, product TEXT, barcode TEXT, quantity INTEGER, unit_price REAL, line_total REAL)
  One row per product sold on an invoice. line_total = quantity * unit_price.

VIEW v_product_stock(product TEXT, barcode TEXT, price REAL, stock INTEGER, expiry_date TEXT 'YYYY-MM-DD')
  Current stock per product. expiry_date can be NULL.

VIEW v_branch_sellers(branch TEXT, seller TEXT, supervisor TEXT)
  One row per seller, with their branch and the branch's supervisor.

STRICT RULES:
- Output exactly ONE SQLite SELECT statement. No explanation, no markdown, no comments.
- Copy the syntax of the examples exactly. Use column names exactly as written above (sale_date, not sale_date_date). Check your parentheses.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, PRAGMA, ATTACH or any other non-SELECT statement.
- Only reference the three views above, never any other table.
- Always include a LIMIT (maximum 500).
- Date filters: today = date('now'), this month = strftime('%Y-%m', 'now'), this year = strftime('%Y', 'now'), last 7 days = date('now', '-7 days').
- "Best seller" means highest SUM(line_total) unless the question asks for quantity.
- If the question cannot be answered from these views, output exactly:
  SELECT 'cannot answer from available data' AS message LIMIT 1;
"""

FEW_SHOT = """Examples:

Q: Who is the best seller this month?
A: SELECT seller, ROUND(SUM(line_total), 2) AS revenue FROM v_sales_detail WHERE strftime('%Y-%m', sale_date) = strftime('%Y-%m', 'now') GROUP BY seller ORDER BY revenue DESC LIMIT 1;

Q: Which branch made the most revenue today?
A: SELECT branch, ROUND(SUM(line_total), 2) AS revenue FROM v_sales_detail WHERE sale_date = date('now') GROUP BY branch ORDER BY revenue DESC LIMIT 1;

Q: What are the top 5 best selling products this year?
A: SELECT product, SUM(quantity) AS units_sold FROM v_sales_detail WHERE strftime('%Y', sale_date) = strftime('%Y', 'now') GROUP BY product ORDER BY units_sold DESC LIMIT 5;

Q: Which products expire in the next 90 days?
A: SELECT product, barcode, stock, expiry_date FROM v_product_stock WHERE expiry_date IS NOT NULL AND expiry_date <= date('now', '+90 days') ORDER BY expiry_date LIMIT 50;

Q: How many sellers work in each branch?
A: SELECT branch, COUNT(seller) AS seller_count FROM v_branch_sellers GROUP BY branch ORDER BY seller_count DESC LIMIT 100;
"""


def build_sql_prompt(question):
    return (
        f'{SCHEMA}\n{FEW_SHOT}\n'
        f"Today's date: {date.today().isoformat()}\n\n"
        f'Q: {question}\nA:'
    )


def build_fix_prompt(question, sql, error):
    return (
        f'{SCHEMA}\n\n'
        f'The following query failed against the database.\n'
        f'Q: {question}\n'
        f'Faulty query: {sql}\n'
        f'Database error: {error}\n\n'
        f'Output ONE corrected SELECT statement only, following all rules above.\nA:'
    )


def build_summary_prompt(question, sql, columns, rows):
    lines = [' | '.join(str(cell) for cell in row) for row in rows[:20]]
    table = '\n'.join(lines) if lines else '(no rows)'
    return (
        'You answer questions using SQL query results. Be brief and factual.\n\n'
        f'Question: {question}\n'
        f'SQL: {sql}\n'
        f'Columns: {" | ".join(columns)}\n'
        f'Result:\n{table}\n\n'
        'Answer the question in one or two short sentences using only the result above. '
        'If the result has no rows, say that no matching data was found.'
    )
