import re

import sqlparse

ALLOWED_TABLES = frozenset({
    'v_sales_detail',
    'v_product_stock',
    'v_branch_sellers',
})
MAX_ROWS = 500

_BLOCKED_RE = re.compile(
    r'\b(insert|update|delete|drop|alter|create|pragma|attach|detach|vacuum|'
    r'truncate|grant|revoke|begin|commit|rollback|savepoint|transaction|'
    r'load_extension|readfile|writefile)\b'
    r'|\breplace\s+into\b'
    r'|\bsqlite_\w+',
    re.IGNORECASE,
)
_TABLE_RE = re.compile(
    r'\b(?:from|join)\s+["`\[]?([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)',
    re.IGNORECASE,
)
_LIMIT_RE = re.compile(r'\blimit\s+(\d+)', re.IGNORECASE)
_FENCE_RE = re.compile(r'```(?:sql|sqlite)?\s*(.*?)```', re.IGNORECASE | re.DOTALL)
_LINE_COMMENT_RE = re.compile(r'--[^\n]*')
_BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


class SqlRejected(Exception):
    pass


def clean_sql(raw):
    text = (raw or '').strip()
    fence = _FENCE_RE.search(text)
    if fence:
        text = fence.group(1)
    text = _BLOCK_COMMENT_RE.sub(' ', text)
    text = _LINE_COMMENT_RE.sub(' ', text)
    return text.strip()


def _single_statement(text):
    statements = [s for s in sqlparse.split(text) if s.strip()]
    if len(statements) != 1:
        raise SqlRejected('expected exactly one SQL statement')
    sql = statements[0].strip().rstrip(';').strip()
    if ';' in sql:
        raise SqlRejected('multiple statements are not allowed')
    if not re.match(r'^(select|with)\b', sql, re.IGNORECASE):
        raise SqlRejected('only SELECT statements are allowed')
    return sql


def _check_blocked(sql):
    match = _BLOCKED_RE.search(sql)
    if match:
        raise SqlRejected(f'forbidden keyword: {match.group(0)!r}')


def _check_tables(sql):
    tables = {
        m.group(1).split('.')[-1].lower()
        for m in _TABLE_RE.finditer(sql)
    }
    unknown = tables - ALLOWED_TABLES
    if unknown:
        raise SqlRejected(
            'only reporting views may be queried, '
            f'got: {", ".join(sorted(unknown))}'
        )


def _enforce_limit(sql):
    match = _LIMIT_RE.search(sql)
    if match:
        if int(match.group(1)) > MAX_ROWS:
            sql = sql[:match.start(1)] + str(MAX_ROWS) + sql[match.end(1):]
        return sql
    return f'{sql} LIMIT {MAX_ROWS}'


def validate_sql(raw):
    sql = _single_statement(clean_sql(raw))
    _check_blocked(sql)
    _check_tables(sql)
    return _enforce_limit(sql)
