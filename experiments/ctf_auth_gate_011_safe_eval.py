"""Evaluate a small, strictly whitelisted subset of Python authorization patches.

No eval(), exec(), imports from a candidate, filesystem or process execution.
Unsupported patch syntax is recorded as UNSUPPORTED_PATCH (not graded as wrong).
"""
import ast

class UnsupportedPatch(ValueError):
    pass

ALLOWED = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.If, ast.Return,
    ast.Name, ast.Load, ast.Constant, ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not, ast.Compare, ast.Eq, ast.NotEq,
)
PARAMS = ("user", "password", "is_admin")
TESTS = [
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
GOLD = """def authorized(user, password, is_admin):
    return user == 'admin' and password == 'correct-horse'
"""
WRONG = """def authorized(user, password, is_admin):
    return True
"""
ORIGINAL = """def authorized(user, password, is_admin):
    if user == 'admin' and password == 'correct-horse':
        return True
    if user != 'admin' and is_admin:
        return True
    return False
"""


def parse_restricted_patch(source):
    if not isinstance(source, str) or not 1 <= len(source.encode("utf-8")) <= 4000:
        raise UnsupportedPatch("Patch must contain 1-4000 UTF-8 bytes")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise UnsupportedPatch("Python syntax error") from exc
    if len(list(ast.walk(tree))) > 100:
        raise UnsupportedPatch("Patch AST too large")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise UnsupportedPatch("Only one Python function is accepted")
    fn = tree.body[0]
    a = fn.args
    if (
        fn.name != "authorized" or [p.arg for p in a.args] != list(PARAMS)
        or a.posonlyargs or a.kwonlyargs or a.vararg or a.kwarg
        or a.defaults or a.kw_defaults or fn.decorator_list
        or fn.returns is not None or fn.type_comment
    ):
        raise UnsupportedPatch("Wrong function signature or decorations")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED):
            raise UnsupportedPatch("Unsafe/unsupported node: " + type(node).__name__)
        if isinstance(node, ast.Name) and node.id not in PARAMS:
            raise UnsupportedPatch("Unknown variable: " + node.id)
        if isinstance(node, ast.Constant) and (
            type(node.value) not in (str, bool)
            or (isinstance(node.value, str) and len(node.value) > 300)
        ):
            raise UnsupportedPatch("Only short string and bool constants are allowed")
        if isinstance(node, ast.Compare) and (
            len(node.ops) != 1 or not isinstance(node.ops[0], (ast.Eq, ast.NotEq))
        ):
            raise UnsupportedPatch("Only simple == and != comparisons are allowed")
    return fn


def evaluate_expr(node, env):
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BoolOp):
        values = [bool(evaluate_expr(item, env)) for item in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not evaluate_expr(node.operand, env)
    if isinstance(node, ast.Compare):
        lhs = evaluate_expr(node.left, env)
        rhs = evaluate_expr(node.comparators[0], env)
        return lhs == rhs if isinstance(node.ops[0], ast.Eq) else lhs != rhs
    raise UnsupportedPatch("Unsupported expression")


_NO_RETURN = object()


def evaluate_block(stmts, env):
    for stmt in stmts:
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                raise UnsupportedPatch("No empty return allowed")
            value = evaluate_expr(stmt.value, env)
            if type(value) is not bool:
                raise UnsupportedPatch("Function must return a boolean")
            return value
        if isinstance(stmt, ast.If):
            branch = stmt.body if evaluate_expr(stmt.test, env) else stmt.orelse
            value = evaluate_block(branch, env)
            if value is not _NO_RETURN:
                return value
    return _NO_RETURN


def check_patch(source):
    fn = parse_restricted_patch(source)
    details = []
    for user, password, is_admin, expected in TESTS:
        actual = evaluate_block(fn.body, dict(zip(PARAMS, (user, password, is_admin))))
        passed = actual is not _NO_RETURN and actual == expected
        details.append({"user": user, "password": password, "is_admin": is_admin,
                        "expected": expected, "actual": actual if actual is not _NO_RETURN else None,
                        "pass": passed})
    return {"passed": all(row["pass"] for row in details),
            "tests_passed": sum(row["pass"] for row in details),
            "tests_total": len(details), "cases": details}


def check_bypass(bypass):
    user, password, is_admin = bypass["user"], bypass["password"], bypass["is_admin"]
    original = (user == "admin" and password == "correct-horse") or (user != "admin" and is_admin)
    intended = (user == "admin" and password == "correct-horse")
    return bool(original and not intended)


def self_test():
    good, bad, flawed = check_patch(GOLD), check_patch(WRONG), check_patch(ORIGINAL)
    assert good["passed"] and not bad["passed"] and not flawed["passed"]
    assert (good["tests_passed"], bad["tests_passed"], flawed["tests_passed"]) == (10, 2, 7)
    assert check_bypass({"user": "guest", "password": "wrong", "is_admin": True})
    assert not check_bypass({"user": "admin", "password": "correct-horse", "is_admin": True})
    for unsafe in ["import os\n", "def authorized(user, password, is_admin):\n    __import__('os')\n    return True\n",
                   "def authorized(user, password, is_admin):\n    while True: pass\n"]:
        try:
            parse_restricted_patch(unsafe)
        except UnsupportedPatch:
            continue
        raise AssertionError("Accepted a forbidden patch")
    return {"good": good["tests_passed"], "bad": bad["tests_passed"],
            "vulnerable": flawed["tests_passed"], "unsafe_rejected": 3}


if __name__ == "__main__":
    import json
    print(json.dumps(self_test()))
