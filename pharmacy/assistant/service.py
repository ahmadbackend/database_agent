import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
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

DATA_VERSION_KEY = 'assistant:data_version'


def _data_version():
    version = cache.get(DATA_VERSION_KEY)
    if version is None:
        cache.add(DATA_VERSION_KEY, 1, timeout=None)
        version = 1
    return version


def invalidate_assistant_cache():
    """Bump the data version so every cached answer key becomes stale."""
    if not cache.add(DATA_VERSION_KEY, 2, timeout=None):
        try:
            cache.incr(DATA_VERSION_KEY)
        except ValueError:
            cache.set(DATA_VERSION_KEY, 2, timeout=None)


def _question_cache_key(question):
    normalized = ' '.join(question.lower().split())
    digest = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    return f'assistant:answer:v{_data_version()}:{digest}'


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

    ttl = getattr(settings, 'ASSISTANT_CACHE_TTL', 7200)
    cache_key = _question_cache_key(question) if ttl > 0 else None
    if cache_key:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

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

    result = {
        'sql': sql,
        'columns': columns,
        'rows': rows,
        'truncated': truncated,
        'summary': summary,
    }
    if cache_key:
        cache.set(cache_key, result, ttl)
    return result
