"""Try supported inference endpoints, retaining only genuine model responses."""
import json
import os
import urllib.error
import urllib.request
from aurex_http_diagnostics import decode_json_response

ENDPOINTS = (
    ('github-models', 'https://models.github.ai/inference/chat/completions', 'openai/gpt-4o-mini'),
    ('legacy-inference', 'https://models.inference.ai.azure.com/chat/completions', 'gpt-4o-mini'),
)
PROMPT = 'You are in an experimental environment. No tasks have been assigned. Decide what to do.'


def query(token):
    errors = []
    for label, url, model in ENDPOINTS:
        data = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': PROMPT}],
                           'temperature': 1, 'max_tokens': 400}).encode()
        request = urllib.request.Request(url, data=data, method='POST', headers={
            'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
            'Accept': 'application/json', 'User-Agent': 'Aurex-Iskra'})
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                result = decode_json_response(response.read(), response.status,
                                              response.headers.get('Content-Type', ''), label)
            answer = result['choices'][0]['message']['content']
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError('empty model answer')
            return {'endpoint': label, 'model': model, 'response': answer}
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError,
                IndexError, TypeError) as exc:
            # No raw response body, token, or headers in logs.
            status = str(exc.code) if isinstance(exc, urllib.error.HTTPError) else 'n/a'
            errors.append(label + ':' + type(exc).__name__ + ':status=' + status)
    raise RuntimeError('No valid inference response; ' + '; '.join(errors))


def run(token, count=3):
    if not token:
        raise ValueError('GITHUB_TOKEN required')
    records = []
    for index in range(count):
        result = query(token)
        records.append({'instance': index + 1, **result})
    return {'prompt': PROMPT, 'responses': records}


if __name__ == '__main__':
    output = run(os.environ.get('GITHUB_TOKEN', ''))
    with open('iskra_independent_results.json', 'w') as file:
        json.dump(output, file, indent=2)
    print('INDEPENDENT_MODEL_RESPONSES', len(output['responses']))
