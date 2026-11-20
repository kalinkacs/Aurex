"""Strict extraction of semantic content from llama-server chat-completions JSON.

This module does not call a model. It deliberately rejects raw CLI stdout,
markdown fences, extra fields, malformed JSON, and malformed claims.
"""
import json

class ResponseFormatError(ValueError):
    pass

def extract_response(payload):
    if not isinstance(payload, dict):
        raise ResponseFormatError("API response is not an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ResponseFormatError("Expected exactly one choice")
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise ResponseFormatError("Generation did not finish normally")
    message = choice.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        raise ResponseFormatError("Missing assistant message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ResponseFormatError("Assistant content is not text")
    try:
        answer = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ResponseFormatError("Assistant content is not strict JSON") from exc
    if not isinstance(answer, dict) or set(answer) != {"bypass", "fixed_source"}:
        raise ResponseFormatError("Wrong answer fields")
    bypass = answer["bypass"]
    if not isinstance(bypass, dict) or set(bypass) != {"user", "password", "is_admin"}:
        raise ResponseFormatError("Wrong bypass fields")
    if not isinstance(bypass["user"], str) or not isinstance(bypass["password"], str):
        raise ResponseFormatError("Bypass credentials must be strings")
    if type(bypass["is_admin"]) is not bool:
        raise ResponseFormatError("is_admin must be boolean")
    if not isinstance(answer["fixed_source"], str) or not answer["fixed_source"].strip():
        raise ResponseFormatError("fixed_source must be nonempty text")
    return answer


def run_canaries():
    valid = {"bypass": {"user": "guest", "password": "wrong", "is_admin": True},
             "fixed_source": "def authorized(user, password, is_admin):\n    return False\n"}
    def wrap(content, finish="stop"):
        return {"choices": [{"finish_reason": finish,
                             "message": {"role": "assistant", "content": content}}]}
    cases = {
        "valid_api_response": (wrap(json.dumps(valid)), True),
        "cli_banner_contamination": (wrap("llama.cpp build banner\n" + json.dumps(valid)), False),
        "markdown_fence": (wrap("```json\n" + json.dumps(valid) + "\n```"), False),
        "missing_field": (wrap(json.dumps({"bypass": valid["bypass"]})), False),
        "wrong_type": (wrap(json.dumps({**valid, "bypass": {**valid["bypass"], "is_admin": "true"}})), False),
        "truncated_generation": (wrap(json.dumps(valid), "length"), False),
        "multiple_choices": ({"choices": [wrap(json.dumps(valid))["choices"][0]] * 2}, False),
    }
    results = {}
    for name, (payload, expected) in cases.items():
        try:
            extract_response(payload)
            accepted = True
        except ResponseFormatError:
            accepted = False
        results[name] = {"expected_accept": expected, "accepted": accepted,
                         "pass": accepted == expected}
    return results


if __name__ == "__main__":
    from pathlib import Path
    results = run_canaries()
    output = Path("receipts/ctf-auth-gate-011-extraction.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"phase": "mock_llama_server_extraction",
                                  "all_pass": all(x["pass"] for x in results.values()),
                                  "results": results}, indent=2), encoding="utf-8")
    print(json.dumps({"all_pass": all(x["pass"] for x in results.values()), "cases": results}))
    raise SystemExit(0 if all(x["pass"] for x in results.values()) else 1)
