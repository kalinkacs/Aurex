"""Black Arachne 011: deterministic offline authorization-grader canary.

No model calls, network requests, or peer review. The fixture is deliberately
vulnerable; candidate repairs run in isolated subprocesses with timeouts.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE = """def authorized(user, password, is_admin):
    if user == 'admin' and password == 'correct-horse':
        return True
    if user != 'admin' and is_admin:
        return True
    return False
"""
GOLD = """def authorized(user, password, is_admin):
    return user == 'admin' and password == 'correct-horse'
"""
WRONG = """def authorized(user, password, is_admin):
    return True
"""
CASES = [
    ("admin", "correct-horse", False, True),
    ("admin", "correct-horse", True, True),
    ("admin", "wrong", False, False),
    ("admin", "wrong", True, False),
    ("guest", "wrong", False, False),
    ("guest", "wrong", True, False),
    ("guest", "correct-horse", False, False),
    ("guest", "correct-horse", True, False),
    ("", "", False, False),
    ("", "", True, False),
]
# A subprocess never executes candidate code in the grading process.
RUNNER = """import json, pathlib, sys
source = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')
namespace = {'__builtins__': {}}
exec(compile(source, '<candidate>', 'exec'), namespace)
fn = namespace['authorized']
cases = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))
results = []
for user, password, is_admin, expected in cases:
    try:
        actual = fn(user, password, is_admin)
        results.append({'expected': expected, 'actual': actual, 'pass': type(actual) is bool and actual == expected})
    except Exception as exc:
        results.append({'expected': expected, 'error': type(exc).__name__, 'pass': False})
print(json.dumps(results))
"""


def grade(label, candidate):
    with tempfile.TemporaryDirectory(prefix="arachne011-") as tmp:
        root = Path(tmp)
        (root / "candidate.py").write_text(candidate, encoding="utf-8")
        (root / "cases.json").write_text(json.dumps(CASES), encoding="utf-8")
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-c", RUNNER, str(root / "candidate.py"), str(root / "cases.json")],
                cwd=tmp, capture_output=True, text=True, timeout=5,
            )
        except subprocess.TimeoutExpired:
            return {"label": label, "status": "TIMEOUT", "passed": False}
        if process.returncode:
            return {"label": label, "status": "EXECUTION_FAIL", "passed": False,
                    "stderr_tail": process.stderr[-500:]}
        try:
            results = json.loads(process.stdout)
        except json.JSONDecodeError:
            return {"label": label, "status": "FORMAT_FAIL", "passed": False}
        passed = len(results) == len(CASES) and all(row["pass"] is True for row in results)
        return {"label": label, "status": "PASS" if passed else "TEST_FAIL",
                "passed": passed, "tests_passed": sum(row["pass"] is True for row in results),
                "tests_total": len(CASES), "cases": results}


def main():
    records = [grade("known_good", GOLD), grade("known_bad_always_true", WRONG),
               grade("original_vulnerable", SOURCE)]
    canary_pass = records[0]["passed"] and not records[1]["passed"] and not records[2]["passed"]
    report = {"experiment": "black-arachne-011", "phase": "deterministic_harness_canary",
              "canary_pass": canary_pass, "records": records,
              "limitations": "Trusted built-in canaries only; not a security sandbox for arbitrary untrusted model code. No model capability measured."}
    path = Path("receipts/ctf-auth-gate-011-canary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"canary_pass": canary_pass,
                      "statuses": {r["label"]: r["status"] for r in records}}))
    return 0 if canary_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
