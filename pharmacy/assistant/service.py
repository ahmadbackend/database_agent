import logging

from django.db import Error as DatabaseError
from django.db import connections

from pharmacy.assistant import ollama_client
from pharmacy.assistant.prompt import (
    build_fix_prompt, build_sql_prompt, build_summary_prompt,
)
from pharmacy.assistant.validate import MAX_ROWS, SqlRejected, validate_sql

logger = logging.getLogger(__name__)

MIN_QUESTION_LEN = 5
MAX_QUESTION_LEN = 500
MAX_ATTEMPTS = 3


def _run_query(sql):
    with connections['readonly'].cursor() as cursor:
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS + 1)
    truncated = len(rows) > MAX_ROWS
    return columns, rows[:MAX_ROWS], truncated


def answer_question(question):
    question = (question or '').strip()
    if not question:
        raise ValueError('Question is empty.')
    if len(question) < MIN_QUESTION_LEN or sum(
        ch.isalpha() for ch in question
    ) < 3:
        raise ValueError(
            'Question is too short — ask a full question '
            f'(at least {MIN_QUESTION_LEN} characters).'
        )
    if len(question) > MAX_QUESTION_LEN:
        raise ValueError(
            f'Question is too long (max {MAX_QUESTION_LEN} characters).'
        )

    prompt = build_sql_prompt(question)
    last_error = None
    sql = columns = rows = truncated = None

    for _ in range(MAX_ATTEMPTS):
        raw = ollama_client.generate(prompt)
        try:
            sql = validate_sql(raw)
            columns, rows, truncated = _run_query(sql)
            break
        except (SqlRejected, DatabaseError) as exc:
            last_error = exc
            prompt = build_fix_prompt(question, raw.strip(), exc)
    else:
        raise RuntimeError(
            'The assistant could not produce a working query. '
            f'Last error: {last_error}'
        )

    summary = None
    try:
        summary = ollama_client.generate(
            build_summary_prompt(question, sql, columns, rows),
            num_predict=150,
        ).strip()
    except ollama_client.OllamaError:
        logger.warning('Summary generation failed', exc_info=True)

    return {
        'sql': sql,
        'columns': columns,
        'rows': rows,
        'truncated': truncated,
        'summary': summary,
    }
