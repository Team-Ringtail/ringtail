from src.utils.code_parser import parse_function


def test_parse_function_python_simple():
    source = '''
def add(a: int, b: int) -> int:
    """Add numbers"""
    return a + b
'''.lstrip()

    info = parse_function(source, language="python")

    assert info["function_name"] == "add"
    param_names = [p["name"] for p in info["parameters"]]
    assert param_names == ["a", "b"]
    assert info["docstring"] == "Add numbers"
    for key in ("name", "lineno", "args_count", "has_decorators"):
        assert key in info["ast_representation"]


def test_parse_function_python_multiple_functions_picks_first():
    source = '''
def first():
    pass

def second():
    pass
'''.lstrip()

    info = parse_function(source, language="python")
    assert info["function_name"] == "first"


def test_parse_function_python_syntax_error_falls_back():
    # Intentionally malformed Python
    source = "def bad(:\n    pass"

    info = parse_function(source, language="python")

    # Should not raise; keys should be present
    assert "function_name" in info
    assert "parameters" in info
    assert "docstring" in info
    assert "ast_representation" in info


def test_parse_function_generic_js_style():
    source = "function foo(x, y) { return x + y; }"

    info = parse_function(source, language="javascript")

    assert info["function_name"] == "foo"
    param_names = [p["name"] for p in info["parameters"]]
    assert param_names == ["x", "y"]
    assert info["docstring"] == ""


def test_parse_function_generic_assigned_function():
    source = "foo = function(x, y) { return x + y; }"

    info = parse_function(source, language="javascript")

    assert info["function_name"] == "foo"
    param_names = [p["name"] for p in info["parameters"]]
    assert param_names == ["x", "y"]


def test_parse_function_docstring_triple_quotes_generic():
    source = '''"""
Docstring before function
"""
def f(x, y):
    return x + y
'''

    # Force generic path to exercise regex docstring logic
    info = parse_function(source, language="javascript")

    assert "Docstring before function" in info["docstring"]

