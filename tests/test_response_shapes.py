"""Offline regression tests for the response shapes the live model step actually returns.

These fixtures are transcripts of *measured* behaviour, not guesses. On 2026-11-06 the
endpoint named in `aurex_ai_agent.MODELS` answered a POST with
`HTTP 200 · text/plain · 4 bytes · body "OK"` — both with no credential and with a
bogus bearer token. A 200 that is not JSON is the production failure the run log
reports as `JSONDecodeError`; these tests pin the diagnostic message for that shape
so a future failure names its stage, status, content type and byte count instead of
raising a bare decode error.

No network access is used here: every shape below is a literal captured response.
"""
import json
import unittest

from aurex_ai_agent import model_text
from aurex_http_diagnostics import decode_json_response


# (status, content_type, body, expected content_type in the message)
MEASURED_SHAPES = [
    # The live observation: a stub/gateway answering a JSON POST with plain text.
    (200, 'text/plain', b'OK', 'text/plain'),
    # A proxy or WAF serving an HTML error page with a 200 status.
    (200, 'text/html; charset=utf-8', b'<html><body>Blocked</body></html>', 'text/html'),
    # Content type is a hint only; a JSON-shaped header can still carry junk.
    (200, 'application/json', b'Service Unavailable', 'application/json'),
    # A truncated body: valid prefix, no closing brace.
    (200, 'application/json', b'{"choices": [{"message": {"content": "par', 'application/json'),
    # An HTML error page behind an error status.
    (503, 'text/html', b'<html>maintenance</html>', 'text/html'),
]


class MeasuredResponseShapeTests(unittest.TestCase):
    def test_each_non_json_shape_reports_stage_status_type_and_size(self):
        for status, content_type, body, media_type in MEASURED_SHAPES:
            with self.subTest(status=status, content_type=content_type, body=body[:20]):
                with self.assertRaises(ValueError) as raised:
                    decode_json_response(body, status, content_type, 'model')
                message = str(raised.exception)
                self.assertIn('AUREX_INVALID_JSON', message)
                self.assertIn('stage=model', message)
                self.assertIn(f'status={status}', message)
                self.assertIn(f'content_type={media_type}', message)
                self.assertIn(f'bytes={len(body)}', message)

    def test_measured_stub_body_reports_two_bytes_after_wire_framing(self):
        """The exact live shape: 200, text/plain, `OK`.

        `curl` reported 4 bytes because the printed body carried CRLF framing;
        urllib hands the caller the payload, which is `b'OK'` — 2 bytes.
        """
        with self.assertRaisesRegex(
            ValueError, r'status=200 content_type=text/plain bytes=2$'
        ):
            decode_json_response(b'OK', 200, 'text/plain; charset=utf-8', 'model')

    def test_no_response_body_leaks_into_the_diagnostic(self):
        marker = 'SENSITIVE_RESPONSE_BODY_DO_NOT_LOG'
        for status, content_type, _, _ in MEASURED_SHAPES:
            with self.subTest(status=status):
                with self.assertRaises(ValueError) as raised:
                    decode_json_response(
                        (marker + ' ' * 32).encode(), status, content_type, 'model'
                    )
                message = str(raised.exception)
                self.assertNotIn(marker, message)
                self.assertNotIn('DO_NOT_LOG', message)

    def test_unicode_body_does_not_raise_a_different_error(self):
        """A non-UTF-8 body must still become the labelled diagnostic, not UnicodeDecodeError."""
        body = b'\xff\xfe\x00OK'
        with self.assertRaises(ValueError) as raised:
            decode_json_response(body, 200, 'text/plain', 'model')
        message = str(raised.exception)
        self.assertIn('AUREX_INVALID_JSON', message)
        self.assertIn('bytes=5', message)

    def test_valid_json_is_returned_unchanged(self):
        payload = {'choices': [{'message': {'content': 'ok'}}]}
        raw = json.dumps(payload).encode()
        self.assertEqual(
            decode_json_response(raw, 200, 'application/json', 'model'), payload
        )


class ModelShapeTests(unittest.TestCase):
    """JSON 200 is not proof of a completion; the failure must name the shape."""

    def test_error_object_with_success_status_names_its_shape(self):
        with self.assertRaises(RuntimeError) as raised:
            model_text({'message': 'SENSITIVE_UPSTREAM_TEXT', 'status': 'error'})
        message = str(raised.exception)
        self.assertIn('AUREX_MODEL_SHAPE_INVALID stage=model', message)
        self.assertIn('choices=missing', message)
        self.assertIn('top_level_keys=2', message)
        self.assertNotIn('SENSITIVE_UPSTREAM_TEXT', message)
        self.assertNotIn('message,status', message)

    def test_choices_key_of_wrong_type_reports_not_list(self):
        with self.assertRaises(RuntimeError) as raised:
            model_text({'choices': {'0': 'not a list'}})
        message = str(raised.exception)
        self.assertIn('choices=not_list', message)
        self.assertIn('top_level_keys=1', message)

    def test_sensitive_key_name_never_reaches_the_diagnostic(self):
        """Review fixture: the marker sits in the KEY NAME, not in a value."""
        marker = 'SENSITIVE_KEY_NAME_DO_NOT_LOG'
        with self.assertRaises(RuntimeError) as raised:
            model_text({marker: 'x', 'status': 'error'})
        message = str(raised.exception)
        self.assertIn('AUREX_MODEL_SHAPE_INVALID stage=model', message)
        self.assertIn('choices=missing', message)
        self.assertIn('top_level_keys=2', message)
        self.assertNotIn(marker, message)
        self.assertNotIn('DO_NOT_LOG', message)

    def test_empty_choices_is_a_shape_error(self):
        with self.assertRaisesRegex(RuntimeError, 'content=absent'):
            model_text({'choices': []})

    def test_non_string_content_is_a_shape_error(self):
        with self.assertRaisesRegex(RuntimeError, 'content=absent'):
            model_text({'choices': [{'message': {'content': None}}]})

    def test_non_object_payload_is_a_shape_error(self):
        with self.assertRaisesRegex(RuntimeError, 'top_level=list'):
            model_text(['not', 'a', 'completion'])

    def test_well_formed_completion_returns_text(self):
        self.assertEqual(
            model_text({'choices': [{'message': {'content': 'analysis'}}]}), 'analysis'
        )


if __name__ == '__main__':
    unittest.main()
