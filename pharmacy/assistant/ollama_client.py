import requests
from django.conf import settings


class OllamaError(Exception):
    pass


def generate(prompt, num_predict=300):
    url = settings.OLLAMA_URL.rstrip('/') + '/api/generate'
    payload = {
        'model': settings.OLLAMA_MODEL,
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': 0,
            'num_predict': num_predict,
            # GPU inference on this machine corrupts tokens; run on CPU.
            'num_gpu': getattr(settings, 'OLLAMA_NUM_GPU', 0),
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=(5, 280))
    except requests.RequestException as exc:
        raise OllamaError(
            f'Cannot reach Ollama at {settings.OLLAMA_URL}: {exc}'
        ) from exc
    if resp.status_code != 200:
        raise OllamaError(
            f'Ollama returned HTTP {resp.status_code}: {resp.text[:200]}'
        )
    return resp.json().get('response', '')
