"""Safe JSON response parsing diagnostics without exposing response bodies."""
import json


def status_class(code):
    """Coarse HTTP status class (2xx, 4xx, ...) for the failure receipt."""
    if isinstance(code, int) and 100 <= code <= 599:
        return f"{code // 100}xx"
    return "unknown"


def decode_json_response(raw, status, content_type, stage):
    """Decode HTTP JSON; on failure raise the one receipt a run reports.

    The receipt carries only the five safe collaboration-record fields:
    stage, HTTP status (with its class), content type, byte count and the
    redacted exception category. Body bytes, header values and error-text
    content never reach the message.
    """
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        media_type = content_type.split(';', 1)[0].strip()
        raise ValueError(
            f"AUREX_INVALID_JSON status_class={status_class(status)} "
            f"type={type(exc).__name__} stage={stage} status={status} "
            f"content_type={media_type} bytes={len(raw)}"
        ) from exc
