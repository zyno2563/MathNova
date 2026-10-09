"""
The tools the assistant may call.

Each one is a thin wrapper over a MathNova engine, so the assistant
answers with results the engines actually computed and verified rather
than arithmetic it performed itself.

Definitions here are provider-neutral: a name, a description, a JSON
Schema, and a callable. Each provider adapter translates that into its
own function-calling format.

Every tool returns a string and never raises — a failure is reported
back to the model as text so it can recover or explain the problem.
"""

import inspect
import re
from typing import Any, Callable, Dict, List

import sympy as sp

from core.safe_parser import parse_math

from core.algebra.linear_algebra import (
    determinant,
    eigenvalues,
    inverse,
    parse_matrix,
)
from core.calculus.calculus import differentiate, integrate
from core.numerical.integration import simpsons_one_third_rule
from core.numerical.root_finding import bisection, newton_raphson
from core.ode.constant_coeff import complementary_function
from core.ode.first_order import (
    bernoulli_equation,
    exact_equation,
    linear_differential_equation,
    variable_separable,
)
from core.pde.first_order import lagrange_linear_pde
from core.transforms.fourier_transform import (
    fourier_cosine_transform,
    fourier_sine_transform,
)
from core.transforms.laplace import inverse_laplace_transform, laplace_transform
from core.transforms.z_transform import inverse_z_transform, z_transform

JSON_TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


class Tool:
    """A callable engine wrapper plus the schema a model needs to call it."""

    def __init__(self, function, name, description, parameters):
        self.function = function
        self.name = name
        self.description = description
        self.parameters = parameters

    def __call__(self, **kwargs):
        return self.function(**kwargs)

    def run(self, arguments):
        """
        Invoke with a model-supplied argument dict.

        Unknown keys are dropped and missing optional keys fall back to
        their defaults, because models occasionally improvise both.
        """

        accepted = inspect.signature(self.function).parameters
        cleaned = {
            key: value for key, value in (arguments or {}).items()
            if key in accepted
        }

        try:
            return str(self.function(**cleaned))
        except TypeError as error:
            return f"{self.name} was called with invalid arguments: {error}"

    def to_json_schema(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


def _docstring_args(doc):
    """Pull `name: description` pairs out of a Google-style Args block."""

    if not doc or "Args:" not in doc:
        return {}

    body = doc.split("Args:", 1)[1]
    descriptions = {}
    current = None

    for line in body.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        match = re.match(r"^(\w+)\s*:\s*(.*)$", stripped)

        if match:
            current = match.group(1)
            descriptions[current] = match.group(2).strip()
        elif current:
            descriptions[current] += " " + stripped

    return descriptions


def tool(function):
    """
    Build a Tool from a function's signature and docstring.

    Keeps each wrapper readable while producing a schema every provider
    can consume.
    """

    doc = inspect.getdoc(function) or ""
    summary = doc.split("Args:", 1)[0].strip()
    arg_docs = _docstring_args(doc)

    properties = {}
    required = []

    for name, parameter in inspect.signature(function).parameters.items():
        annotation = parameter.annotation
        schema = {"type": JSON_TYPES.get(annotation, "string")}

        if name in arg_docs:
            schema["description"] = arg_docs[name]

        properties[name] = schema

        if parameter.default is inspect.Parameter.empty:
            required.append(name)

    return Tool(
        function=function,
        name=function.__name__,
        description=summary,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


# =========================================================
# Helpers
# =========================================================

def _guard(label, function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except Exception as error:  # noqa: BLE001 - reported to the model
        return f"{label} failed: {error}"


def _show(expression):
    return sp.sstr(expression)


def _verified(result):
    flag = result.get("verified")

    if flag is True:
        return " [symbolically verified]"
    if flag is False:
        return " [could not be auto-verified]"

    return ""


def _coefficients(text):
    values = []

    for part in str(text).split(","):
        part = part.strip()

        if part:
            values.append(parse_math(part))

    if len(values) < 2:
        raise ValueError("At least two coefficients are required.")

    return values


# =========================================================
# Engine tools
# =========================================================

@tool
def differentiate_expression(expression: str) -> str:
    """Differentiate an expression with respect to x.

    Args:
        expression: The expression in x, for example "x^2*sin(x)".
    """

    outcome = _guard("Differentiation", differentiate, expression)

    if isinstance(outcome, str):
        return outcome

    return f"d/dx [{expression}] = {_show(outcome)}"


@tool
def integrate_expression(expression: str) -> str:
    """Compute the indefinite integral of an expression with respect to x.

    Args:
        expression: The expression in x, for example "x*exp(x)".
    """

    outcome = _guard("Integration", integrate, expression)

    if isinstance(outcome, str):
        return outcome

    return f"integral of {expression} dx = {_show(outcome)} + C"


@tool
def solve_homogeneous_ode(coefficients: str) -> str:
    """Solve a constant-coefficient homogeneous ODE F(D)y = 0.

    Returns the auxiliary equation, its roots, and the complementary function.

    Args:
        coefficients: Operator coefficients in descending powers of D,
            comma separated. For (D^2 - 3D + 2)y = 0 pass "1, -3, 2".
    """

    try:
        values = _coefficients(coefficients)
    except Exception as error:  # noqa: BLE001
        return f"Invalid coefficients: {error}"

    outcome = _guard("Solving the ODE", complementary_function, values)

    if isinstance(outcome, str):
        return outcome

    auxiliary, roots, cf = outcome

    root_text = ", ".join(
        f"m = {_show(root)} (multiplicity {multiplicity})"
        for root, multiplicity in roots.items()
    )

    return (
        f"Auxiliary equation: {_show(auxiliary)} = 0\n"
        f"Roots: {root_text}\n"
        f"Complementary function: y = {_show(cf)}"
    )


@tool
def solve_first_order_ode(
    method: str,
    first: str,
    second: str,
    n: str = ""
) -> str:
    """Solve a first-order ODE by a named method.

    Args:
        method: One of "separable", "linear", "bernoulli", "exact".
        first: For "separable" the f(x) in dy/dx = f(x)g(y); for "linear"
            and "bernoulli" the P(x) in dy/dx + P(x)y = Q(x)[y^n]; for
            "exact" the M(x,y) in M dx + N dy = 0.
        second: For "separable" the g(y); for "linear"/"bernoulli" the
            Q(x); for "exact" the N(x,y).
        n: The exponent n, required only for "bernoulli".
    """

    method = method.strip().lower()

    if method == "separable":
        outcome = _guard("Separation of variables", variable_separable, first, second)
    elif method == "linear":
        outcome = _guard(
            "Integrating factor method", linear_differential_equation, first, second
        )
    elif method == "bernoulli":
        if not n:
            return "The 'bernoulli' method requires the exponent n."
        outcome = _guard(
            "Bernoulli substitution", bernoulli_equation, first, second, n
        )
    elif method == "exact":
        outcome = _guard("Exactness test", exact_equation, first, second)
    else:
        return "Unknown method. Use separable, linear, bernoulli, or exact."

    if isinstance(outcome, str):
        return outcome

    return f"Solution: {_show(outcome['solution'])}{_verified(outcome)}"


@tool
def compute_laplace_transform(function: str) -> str:
    """Compute the Laplace transform F(s) of a function f(t).

    Args:
        function: f(t), for example "sin(2*t)" or "t^2*exp(-t)".
    """

    outcome = _guard("Laplace transform", laplace_transform, function)

    if isinstance(outcome, str):
        return outcome

    return f"L{{{function}}} = {_show(outcome['F'])}{_verified(outcome)}"


@tool
def compute_inverse_laplace_transform(function: str) -> str:
    """Compute the inverse Laplace transform f(t) of F(s).

    Args:
        function: F(s), for example "1/(s^2+4)".
    """

    outcome = _guard(
        "Inverse Laplace transform", inverse_laplace_transform, function
    )

    if isinstance(outcome, str):
        return outcome

    return f"L^-1{{{function}}} = {_show(outcome['f'])}{_verified(outcome)}"


@tool
def compute_fourier_transform(function: str, kind: str = "sine") -> str:
    """Compute the Fourier sine or cosine transform of f(x) for x > 0.

    Args:
        function: f(x), for example "exp(-2*x)".
        kind: Either "sine" or "cosine".
    """

    if kind.strip().lower() == "cosine":
        outcome = _guard(
            "Fourier cosine transform", fourier_cosine_transform, function
        )
        key = "Fc"
    else:
        outcome = _guard(
            "Fourier sine transform", fourier_sine_transform, function
        )
        key = "Fs"

    if isinstance(outcome, str):
        return outcome

    return f"{key}(w) = {_show(outcome[key])}{_verified(outcome)}"


@tool
def compute_z_transform(sequence: str) -> str:
    """Compute the Z-transform X(z) of a discrete sequence x(n), n >= 0.

    Args:
        sequence: x(n), for example "a^n" or "n*2^n" or "cos(n*theta)".
    """

    outcome = _guard("Z-transform", z_transform, sequence)

    if isinstance(outcome, str):
        return outcome

    return f"Z{{{sequence}}} = {_show(outcome['X'])}{_verified(outcome)}"


@tool
def compute_inverse_z_transform(function: str) -> str:
    """Compute the inverse Z-transform x(n) of a rational X(z).

    Args:
        function: X(z), for example "z/((z-1)*(z-2))".
    """

    outcome = _guard("Inverse Z-transform", inverse_z_transform, function)

    if isinstance(outcome, str):
        return outcome

    return f"x(n) = {_show(outcome['x_n'])}{_verified(outcome)}"


@tool
def solve_lagrange_pde(P: str, Q: str, R: str) -> str:
    """Solve Lagrange's linear PDE Pp + Qq = R.

    Args:
        P: The coefficient P(x, y, z) of p = dz/dx.
        Q: The coefficient Q(x, y, z) of q = dz/dy.
        R: The right-hand side R(x, y, z).
    """

    outcome = _guard("Lagrange's method", lagrange_linear_pde, P, Q, R)

    if isinstance(outcome, str):
        return outcome

    return (
        f"First invariant:  u = {_show(outcome['u'])}\n"
        f"Second invariant: v = {_show(outcome['v'])}\n"
        f"General solution: F(u, v) = 0{_verified(outcome)}"
    )


@tool
def find_root(function: str, method: str = "bisection",
              a: float = 0.0, b: float = 1.0) -> str:
    """Find a numerical root of f(x) = 0.

    Args:
        function: f(x), for example "x^3 - x - 2".
        method: Either "bisection" (needs a bracket a, b with a sign
            change) or "newton" (uses a as the initial guess).
        a: Bracket start for bisection, or the initial guess for newton.
        b: Bracket end, used only by bisection.
    """

    if method.strip().lower() == "newton":
        outcome = _guard("Newton-Raphson", newton_raphson, function, a)
    else:
        outcome = _guard("Bisection", bisection, function, a, b)

    if isinstance(outcome, str):
        return outcome

    return (
        f"root ~= {outcome['root']:.10g} after "
        f"{outcome['iterations_count']} iterations "
        f"(residual {outcome['residual']:.3e})"
    )


@tool
def integrate_numerically(function: str, a: float, b: float, n: int = 10) -> str:
    """Integrate f(x) over [a, b] numerically using Simpson's 1/3 rule.

    Args:
        function: f(x), for example "exp(-x^2)".
        a: Lower limit.
        b: Upper limit.
        n: Number of subintervals; must be even.
    """

    n = int(n)

    if n % 2 != 0:
        n += 1

    outcome = _guard(
        "Simpson's rule", simpsons_one_third_rule, function, float(a), float(b), n
    )

    if isinstance(outcome, str):
        return outcome

    exact = outcome.get("exact_integral")
    exact_text = f", exact value {exact:.10g}" if exact is not None else ""

    return (
        f"integral from {a} to {b} of {function} dx "
        f"~= {outcome['integral']:.10g} (Simpson 1/3, n={n}){exact_text}"
    )


@tool
def analyse_matrix(matrix: str) -> str:
    """Compute the determinant, inverse and eigenvalues of a square matrix.

    Args:
        matrix: Rows separated by newlines and values by commas,
            for example "2, 1\\n1, 2".
    """

    parsed = _guard("Reading the matrix", parse_matrix, matrix)

    if isinstance(parsed, str):
        return parsed

    if parsed.rows != parsed.cols:
        return "That matrix is not square, so it has no determinant or eigenvalues."

    lines = [f"Matrix: {_show(parsed)}"]

    det = _guard("Determinant", determinant, parsed)
    lines.append(f"det(A) = {det if isinstance(det, str) else _show(det)}")

    inv = _guard("Inverse", inverse, parsed)
    lines.append(f"A^-1 = {inv if isinstance(inv, str) else _show(inv)}")

    values = _guard("Eigenvalues", eigenvalues, parsed)

    if isinstance(values, str):
        lines.append(values)
    else:
        lines.append(
            "Eigenvalues: "
            + ", ".join(
                f"{_show(value)} (multiplicity {multiplicity})"
                for value, multiplicity in values.items()
            )
        )

    return "\n".join(lines)


TOOLS: List[Tool] = [
    differentiate_expression,
    integrate_expression,
    solve_homogeneous_ode,
    solve_first_order_ode,
    compute_laplace_transform,
    compute_inverse_laplace_transform,
    compute_fourier_transform,
    compute_z_transform,
    compute_inverse_z_transform,
    solve_lagrange_pde,
    find_root,
    integrate_numerically,
    analyse_matrix,
]

TOOLS_BY_NAME: Dict[str, Tool] = {item.name: item for item in TOOLS}
