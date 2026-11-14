"""Bounded Groq connectivity smoke test; never prints credentials or response bodies."""
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("AUREX_GROQ_MODEL", "llama-3.1-8b-instant")

def main():
    key = os.getenv("GROQ_SECRET_API", "").strip()
    if not key:
        print("AUREX_GROQ_MISSING_SECRET")
        return 2
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": "Reply with exactly AUREX_GROQ_OK"}],
        "temperature": 0,
        "max_tokens": 32,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=payload, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read(32769)
            status = response.status
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        print(f"AUREX_GROQ_HTTP_FAILURE status={exc.code}")
        return 1
    except (urllib.error.URLError, TimeoutError):
        print("AUREX_GROQ_TRANSPORT_FAILURE")
        return 1
    if len(raw) > 32768:
        print("AUREX_GROQ_RESPONSE_TOO_LARGE")
        return 1
    if content_type != "application/json":
        print(f"AUREX_GROQ_NON_JSON status={status} bytes={len(raw)}")
        return 1
    try:
        data = json.loads(raw)
        answer = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        print(f"AUREX_GROQ_INVALID_RESPONSE status={status} bytes={len(raw)}")
        return 1
    passed = isinstance(answer, str) and answer.strip() == "AUREX_GROQ_OK"
    print("AUREX_GROQ_SMOKE_" + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1

if __name__ == "__main__":
    sys.exit(main())
