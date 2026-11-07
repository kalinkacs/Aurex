"""Log-safety invariant: no response body, header value or token reaches the run log.

Issue #6 asks that diagnostics never print response bodies, credentials or private
data. The unit tests next door check the exception message; this file checks the
place the message actually goes — stdout/stderr of the workflow step — by running the
agent's real failure path under `runpy` with a stub transport and scanning everything
it emitted.

The invariant is deliberately blunt: after a failed run, the captured output must not
contain the response body marker, the bearer token, or the request headers.
"""
import io
import os
import runpy
import unittest
from unittest.mock import patch

BODY_MARKER = 'SENSITIVE_RESPONSE_BODY_DO_NOT_LOG'
TOKEN = 'ghs_FAKE_TOKEN_DO_NOT_LOG_0123456789'


class _StubResponse:
    """Minimal stand-in for `http.client.HTTPResponse` used by urllib."""

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


def _run_agent(monkey_response=None, monkey_error=None):
    """Execute aurex_ai_agent as __main__ and return (stdout, stderr, exit_code)."""
    out, err = io.StringIO(), io.StringIO()
    env = {
        'GITHUB_TOKEN': TOKEN,
        'GITHUB_REPOSITORY': 'kalinkacs/Aurex',
        'AUREX_ISSUE_NUMBER': '6',
    }
    patch_target = 'urllib.request.urlopen'
    with patch.dict(os.environ, env, clear=False), \
            patch(patch_target, side_effect=monkey_error) if monkey_error \
            else patch(patch_target, return_value=monkey_response):
        import contextlib
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                runpy.run_module('aurex_ai_agent', run_name='__main__')
                code = 0
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    return out.getvalue(), err.getvalue(), code


class LogSafetyTests(unittest.TestCase):
    def assert_clean(self, output):
        self.assertNotIn(BODY_MARKER, output)
        self.assertNotIn(TOKEN, output)
        self.assertNotIn('Authorization', output)
        self.assertNotIn('Bearer', output)

    def test_non_json_200_prints_labelled_diagnostic_only(self):
        stub = _StubResponse(200, (BODY_MARKER + ' ' * 8).encode(), 'text/plain')
        stdout, stderr, code = _run_agent(monkey_response=stub)
        combined = stdout + stderr
        self.assertEqual(code, 1)
        self.assertIn('AUREX_INVALID_JSON', combined)
        self.assertIn('status=200', combined)
        self.assertIn('content_type=text/plain', combined)
        self.assert_clean(combined)

    def test_forbidden_response_prints_status_only(self):
        import urllib.error
        error = urllib.error.HTTPError(
            'https://models.github.ai/inference/chat/completions',
            403, 'Forbidden', {}, io.BytesIO(BODY_MARKER.encode()),
        )
        stdout, stderr, code = _run_agent(monkey_error=error)
        combined = stdout + stderr
        self.assertEqual(code, 1)
        self.assertIn('AUREX_HTTP_FAILURE', combined)
        self.assertIn('status=403', combined)
        self.assert_clean(combined)

    def test_json_error_object_does_not_print_its_values(self):
        """A 200 JSON error body must be reported by shape, never by content."""
        body = ('{"message": "' + BODY_MARKER + '", "status": "error"}').encode()
        stub = _StubResponse(200, body, 'application/json')
        _, stderr, code = _run_agent(monkey_response=stub)
        self.assertEqual(code, 1)
        self.assertIn('AUREX_MODEL_SHAPE_INVALID', stderr)
        self.assertIn('keys=message,status', stderr)
        self.assert_clean(stderr)

    def test_html_error_page_does_not_reach_the_log(self):
        stub = _StubResponse(502, (BODY_MARKER + '<html>').encode(), 'text/html')
        _, stderr, code = _run_agent(monkey_response=stub)
        self.assertEqual(code, 1)
        self.assertIn('AUREX_INVALID_JSON', stderr)
        self.assert_clean(stderr)


if __name__ == '__main__':
    unittest.main()
