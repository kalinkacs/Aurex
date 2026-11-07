"""The five-field receipt law on every path where the model call dies.

The collaboration record settles the receipt for one dispatch as exactly five
safe fields: stage, HTTP status class, content type, byte count and the redacted
exception category — and no payload bytes, tokens or header values anywhere.

PR #24 pinned the decode-level receipt's stage/status/content_type/bytes. This
file pins the two fields the record adds: the status class and the redacted
exception category, plus the transport-level receipt that previously named only
stage and status. The line layout keeps PR #24's pinned
`status=... content_type=... bytes=...` core contiguous, so the two PRs compose.

No network access. Tokens below are synthetic and asserted absent from output.
"""
import io
import unittest
import urllib.error
from unittest.mock import patch

from aurex_ai_agent import request_json
from aurex_http_diagnostics import decode_json_response, status_class

BODY_MARKER = 'SENSITIVE_RESPONSE_BODY_DO_NOT_LOG'
TOKEN = 'ghs_FAKE_TOKEN_DO_NOT_LOG_0123456789'
MODELS_URL = 'https://models.github.ai/inference/chat/completions'


class StatusClassTests(unittest.TestCase):
    def test_known_codes_classify(self):
        self.assertEqual(status_class(200), '2xx')
        self.assertEqual(status_class(403), '4xx')
        self.assertEqual(status_class(503), '5xx')

    def test_unknown_inputs_are_reported_not_crushed(self):
        self.assertEqual(status_class(None), 'unknown')
        self.assertEqual(status_class('503'), 'unknown')
        self.assertEqual(status_class(99), 'unknown')
        self.assertEqual(status_class(600), 'unknown')


class DecodeReceiptLawTests(unittest.TestCase):
    def test_receipt_names_all_five_fields(self):
        with self.assertRaises(ValueError) as raised:
            decode_json_response(b'OK', 200, 'text/plain; charset=utf-8', 'model')
        message = str(raised.exception)
        for field in ('stage=model', 'status=200', 'status_class=2xx',
                      'content_type=text/plain', 'bytes=2',
                      'type=JSONDecodeError'):
            self.assertIn(field, message)
        self.assertIn('AUREX_INVALID_JSON', message)

    def test_truncated_and_unicode_bodies_get_distinct_categories(self):
        cases = [
            (b'{"choices": [{"message": {"content": "par', 'application/json',
             'JSONDecodeError'),
            (b'\xff\xfe\x00OK', 'text/plain', 'UnicodeDecodeError'),
        ]
        for raw, ctype, category in cases:
            with self.subTest(category=category):
                with self.assertRaises(ValueError) as raised:
                    decode_json_response(raw, 200, ctype, 'model')
                message = str(raised.exception)
                self.assertIn('type=' + category, message)
                self.assertIn('AUREX_INVALID_JSON', message)
                self.assertNotIn(BODY_MARKER, message)

    def test_exception_category_is_redacted(self):
        """The category names the exception type, never its message text."""
        with self.assertRaises(ValueError) as raised:
            decode_json_response(
                (BODY_MARKER + ' trailing junk {').encode(), 200,
                'application/json', 'model')
        message = str(raised.exception)
        self.assertIn('type=JSONDecodeError', message)
        self.assertNotIn(BODY_MARKER, message)
        self.assertNotIn('Expecting', message)


class _StubResponse:
    """Minimal stand-in for the object urlopen returns."""

    def __init__(self, status, body, content_type):
        self.status = status
        self._body = body
        self.headers = {'Content-Type': content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class HTTPErrorReceiptLawTests(unittest.TestCase):
    def _http_error(self, code, ctype, body):
        headers = {} if ctype is None else {'Content-Type': ctype}
        return urllib.error.HTTPError(
            MODELS_URL, code, 'Forbidden', headers, io.BytesIO(body))

    def test_model_stage_receipt_carries_all_five_fields(self):
        body = (BODY_MARKER + ' padding').encode()
        err = self._http_error(403, 'text/html; charset=utf-8', body)
        with patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError) as raised:
                request_json(MODELS_URL, TOKEN, payload={'x': 1})
        message = str(raised.exception)
        for field in ('stage=model', 'status=403', 'status_class=4xx',
                      'content_type=text/html',
                      'bytes=' + str(len(body)), 'type=HTTPError'):
            self.assertIn(field, message)
        self.assertIn('AUREX_HTTP_FAILURE', message)
        self.assertNotIn(BODY_MARKER, message)
        self.assertNotIn(TOKEN, message)
        self.assertNotIn('Authorization', message)
        self.assertNotIn('Forbidden', message)

    def test_missing_content_type_reports_none_not_a_crash(self):
        body = b'<html>maintenance</html>'
        err = self._http_error(503, None, body)
        with patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError) as raised:
                request_json('https://api.github.com/repos/x/y/z', TOKEN)
        message = str(raised.exception)
        self.assertIn('stage=github', message)
        self.assertIn('status=503', message)
        self.assertIn('status_class=5xx', message)
        self.assertIn('content_type=none', message)
        self.assertIn('bytes=' + str(len(body)), message)
        self.assertIn('AUREX_HTTP_FAILURE', message)
        self.assertNotIn('<html>', message)

    def test_receipt_is_raised_when_error_body_cannot_be_read(self):
        """A unreadable error body degrades to bytes=0, never to a leak."""
        err = self._http_error(500, 'text/plain', b'')
        err.fp = None  # simulate a transport that handed over no body at all
        with patch('urllib.request.urlopen', side_effect=err):
            with self.assertRaises(RuntimeError) as raised:
                request_json(MODELS_URL, TOKEN)
        message = str(raised.exception)
        self.assertIn('status=500', message)
        self.assertIn('status_class=5xx', message)
        self.assertIn('type=HTTPError', message)
        self.assertIn('AUREX_HTTP_FAILURE', message)

    def test_success_path_is_unchanged(self):
        payload = b'{"choices": [{"message": {"content": "ok"}}]}'
        with patch('urllib.request.urlopen',
                   return_value=_StubResponse(200, payload, 'application/json')):
            self.assertEqual(request_json(MODELS_URL, TOKEN)['choices'][0]
                             ['message']['content'], 'ok')


if __name__ == '__main__':
    unittest.main()
