"""The public math language cannot invoke Python or implicit string parsing."""

import pytest
import sympy as sp
from fastapi.testclient import TestClient

from core.safe_parser import parse_math


@pytest.mark.parametrize("source, expected", [
    ("1/3 + 2/3", sp.Integer(1)),
    ("sin(pi/2) + cos(0)", sp.Integer(2)),
    ("sqrt(2)^2 + exp(0)", sp.Integer(3)),
    ("log(e) + Abs(-2)", sp.Integer(3)),
    ("factorial(5) + binomial(5, 2)", sp.Integer(130)),
    ("I^2", sp.Integer(-1)),
    ("2e-7", sp.Float("2e-7")),
    ("0.123456789123456789", sp.Float("0.123456789123456789")),
])
def test_supported_numeric_math_keeps_exact_values(source, expected):
    assert parse_math(source) == expected


def test_symbol_bindings_and_assumptions_survive():
    from core.transforms.laplace import parse_expression
    from core.transforms.utils import t
    from core.transforms.z_transform import parse_expression as parse_z
    from core.transforms.utils import n

    assert parse_expression("t^2 + a").has(t)
    result = parse_z("a^n")
    assert n in result.free_symbols
    assert all(symbol.is_real for symbol in result.free_symbols)


def test_piecewise_comparisons_and_logical_conditions():
    x = sp.Symbol("x", real=True)
    expression = parse_math("Piecewise((x^2, -1 <= x < 1), (0, True))", locals={"x": x})
    assert expression.subs(x, sp.Rational(1, 2)) == sp.Rational(1, 4)
    assert expression.subs(x, 2) == 0
    expression = parse_math("Piecewise((x, (x > 0) & (x < 2)), (-x, True))", locals={"x": x})
    assert expression.subs(x, -1) == 1


@pytest.mark.parametrize("source", [
    "__import__('math').sqrt(4)", "x.__class__", "sin.__globals__",
    "getattr(x, 'name')", "eval('1+1')", "open('example.txt')",
    "(lambda: 1)()", "[x for x in (1, 2)]", "x[0]", "{'x': 1}",
    "(x := 1)", "'x'", "[1, 2]", "(1, 2)", "f(x)",
    "sin(x, evaluate=False)", "sin(*[x])", "Symbol('x')", "Matrix([[1]])",
    "Piecewise((x, x), (0, True))", "1e309", "2**(2**100)",
    "factorial(1000000)", "x**1000000000",
])
def test_non_math_syntax_is_rejected_without_execution(source):
    with pytest.raises(ValueError):
        parse_math(source)


def test_bindings_cannot_add_callable_code():
    calls = []
    with pytest.raises(ValueError):
        parse_math("probe()", locals={"probe": lambda: calls.append(True)})
    assert calls == []


@pytest.mark.parametrize("source", ["x" * 4001, "sin(" * 50 + "x" + ")" * 50,
                                   "+".join(["x"] * 300)])
def test_input_size_and_depth_are_bounded(source):
    with pytest.raises(ValueError):
        parse_math(source)


def test_every_engine_parser_and_matrix_entry_path_uses_the_safe_language():
    from core.calculus.calculus import parse_expression as calculus
    from core.calculus.parser import parse_function
    from core.numerical.utils import parse_expression as numerical
    from core.ode.constant_coeff import parse_expression as ode
    from core.ode.first_order import parse_expression as first_order
    from core.pde.first_order import parse_expression as pde
    from core.transforms.laplace import parse_expression as laplace, inverse_laplace_transform
    from core.transforms.fourier_transform import parse_expression as fourier, inverse_fourier_transform
    from core.transforms.z_transform import parse_expression as z, inverse_z_transform
    from core.algebra.linear_algebra import create_matrix, parse_matrix
    from backend.assistant.tools import _coefficients
    from backend.routers.ode import to_exact
    from backend.errors import InvalidInput

    for parse in (calculus, parse_function, numerical, ode, first_order, pde,
                  laplace, inverse_laplace_transform, fourier, inverse_fourier_transform,
                  z, inverse_z_transform, _coefficients):
        with pytest.raises(ValueError):
            parse("sin(x).__class__")
    with pytest.raises(InvalidInput):
        to_exact("sin(x).__class__")
    with pytest.raises(ValueError):
        create_matrix([["sin(x).__class__"]])
    with pytest.raises(ValueError):
        parse_matrix("sin(x).__class__")
    assert create_matrix([["1/3", "sqrt(2)"]]) == sp.Matrix([[sp.Rational(1, 3), sp.sqrt(2)]])


@pytest.mark.parametrize("path, body", [
    ("/api/calculus/differentiate", {"expression": "sin(x).__class__"}),
    ("/api/fourier/series", {"expression": "sin(x).__class__"}),
    ("/api/linear-algebra/analyze", {"matrix": "sin(x).__class__"}),
    ("/api/linear-algebra/analyze", {"rows": [["sin(x).__class__"]]}),
    ("/api/ode/complementary-function", {"coefficients": [1, "sin(x).__class__"]}),
    ("/api/transforms/laplace/inverse", {"function": "sin(x).__class__"}),
])
def test_http_rejections_are_clean_input_errors(path, body):
    from backend.main import app
    with TestClient(app) as client:
        response = client.post(path, json=body)
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "invalid_input"


def test_fourier_parses_inside_guard_before_compiling_the_callable(monkeypatch):
    from backend.routers import fourier
    from backend.errors import solve
    calls = []

    def tracked(operation, function, *args, **kwargs):
        calls.append((function.__name__, kwargs.get("isolated", True)))
        return solve(operation, function, *args, **kwargs)

    monkeypatch.setattr(fourier, "solve", tracked)
    fourier.fourier_series(fourier.SeriesRequest(expression="x", terms=1, points=20))
    assert ("parse_symbolic_function", True) in calls
    assert ("function_from_expression", False) in calls


@pytest.mark.parametrize("endpoint, body", [
    ("complementary_function_endpoint", {"coefficients": [1, "-3", 2]}),
    ("particular_integral_endpoint", {"coefficients": [1, "-3", 2],
                                     "forcing": {"type": "polynomial", "expression": "x"}}),
    ("complete_solution_endpoint", {"coefficients": [1, "-3", 2],
                                   "forcing": {"type": "polynomial", "expression": "x"}}),
])
def test_ode_parses_coefficients_inside_the_computation_guard(monkeypatch, endpoint, body):
    from backend.routers import ode
    from backend.errors import solve
    calls = []

    def tracked(operation, function, *args, **kwargs):
        calls.append((function.__name__, kwargs.get("isolated", True)))
        return solve(operation, function, *args, **kwargs)

    monkeypatch.setattr(ode, "solve", tracked)
    model = ode.ParticularIntegralRequest if "forcing" in body else ode.CoefficientsRequest
    getattr(ode, endpoint)(model(**body))
    assert ("_exact_coefficients", True) in calls
