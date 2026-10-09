"""
Ordinary differential equation endpoints.

Wraps core.ode.constant_coeff (CF / PI / complete solution) and
core.ode.first_order (separable, linear, Bernoulli, exact).
"""

from typing import List, Literal, Optional, Union

import sympy as sp

from core.safe_parser import parse_math
from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from backend.errors import InvalidInput, solve
from backend.limits import number
from backend.serialization import serialize, success
from core.ode.constant_coeff import (
    build_complete_solution,
    complementary_function,
    particular_integral_exponential,
    particular_integral_exponential_function,
    particular_integral_polynomial,
    particular_integral_trigonometric,
)
from core.ode.first_order import (
    bernoulli_equation,
    exact_equation,
    linear_differential_equation,
    variable_separable,
)

router = APIRouter(prefix="/ode", tags=["ode"])

ForcingType = Literal[
    "exponential", "sine", "cosine", "polynomial", "exponential_function"
]


def to_exact(value):
    """
    Convert a JSON number or string into an exact SymPy value.

    Going through Rational(str(...)) keeps 0.5 as 1/2 rather than a
    binary float, so downstream results stay in closed form.
    """

    if isinstance(value, str):
        text = value.strip()

        if not text:
            raise InvalidInput("Empty coefficient.")

        try:
            return parse_math(text)
        except ValueError as error:
            raise InvalidInput(f"Invalid coefficient: {error}") from error

    return sp.Rational(str(value))


def _exact_coefficients(values):
    """Run string parsing inside the computation guard, as one operation."""
    return [to_exact(value) for value in values]


class Forcing(BaseModel):
    """The right-hand side X of F(D)y = X."""

    type: ForcingType
    a: Optional[float] = number(
        "Parameter a for e^(ax), sin(ax), cos(ax)", default=None
    )
    expression: Optional[str] = Field(
        default=None,
        max_length=300,
        description="X(x) for a polynomial, or V(x) for e^(ax)V(x)"
    )

    @model_validator(mode="after")
    def check_fields(self):
        needs_a = ("exponential", "sine", "cosine", "exponential_function")
        needs_expression = ("polynomial", "exponential_function")

        if self.type in needs_a and self.a is None:
            raise ValueError(f"forcing.a is required for type '{self.type}'")

        if self.type in needs_expression and not self.expression:
            raise ValueError(
                f"forcing.expression is required for type '{self.type}'"
            )

        return self


class CoefficientsRequest(BaseModel):
    coefficients: List[Union[float, int, str]] = Field(
        ...,
        description=(
            "Operator coefficients in descending powers of D. "
            "D^2 - 3D + 2 is [1, -3, 2]."
        ),
        examples=[[1, -3, 2]]
    )

    @model_validator(mode="after")
    def check_length(self):
        if len(self.coefficients) < 2:
            raise ValueError("At least two coefficients are required")

        if len(self.coefficients) > 8:
            raise ValueError("At most 8 coefficients are supported")

        # A coefficient may be given symbolically ("a", "2*k"), so each
        # one is parsed. Bound them individually: the list length alone
        # does not stop one enormous expression.
        for value in self.coefficients:
            if isinstance(value, str) and len(value) > 60:
                raise ValueError(
                    "Each coefficient must be at most 60 characters"
                )

            if isinstance(value, float) and (
                value != value or value in (float("inf"), float("-inf"))
            ):
                raise ValueError("Coefficients must be finite numbers")

        return self


class ParticularIntegralRequest(CoefficientsRequest):
    forcing: Forcing


def _compute_particular_integral(coefficients, forcing):
    """
    Dispatch to the right PI engine and also return the forcing term
    as text, which build_complete_solution needs for verification.
    """

    if forcing.type == "exponential":
        a = to_exact(forcing.a)
        result = solve(
            "Computing the particular integral",
            particular_integral_exponential, coefficients, a
        )
        return result, f"exp({sp.sstr(a)}*x)"

    if forcing.type in ("sine", "cosine"):
        a = to_exact(forcing.a)
        kind = "sin" if forcing.type == "sine" else "cos"
        result = solve(
            "Computing the particular integral",
            particular_integral_trigonometric, coefficients, a, kind
        )
        return result, f"{kind}({sp.sstr(a)}*x)"

    if forcing.type == "polynomial":
        result = solve(
            "Computing the particular integral",
            particular_integral_polynomial, coefficients, forcing.expression
        )
        return result, forcing.expression

    a = to_exact(forcing.a)
    result = solve(
        "Computing the particular integral",
        particular_integral_exponential_function,
        coefficients, a, forcing.expression
    )
    return result, f"exp({sp.sstr(a)}*x)*({forcing.expression})"


@router.post("/complementary-function", summary="Solve F(D)y = 0")
def complementary_function_endpoint(request: CoefficientsRequest):
    coefficients = solve("Reading coefficients", _exact_coefficients, request.coefficients)

    auxiliary, roots, cf = solve(
        "Computing the complementary function",
        complementary_function, coefficients
    )

    return success({
        "auxiliary_equation": serialize(auxiliary),
        "roots": [
            {"root": serialize(root), "multiplicity": int(multiplicity)}
            for root, multiplicity in roots.items()
        ],
        "complementary_function": serialize(cf)
    })


@router.post("/particular-integral", summary="Solve F(D)y = X for the PI")
def particular_integral_endpoint(request: ParticularIntegralRequest):
    coefficients = solve("Reading coefficients", _exact_coefficients, request.coefficients)

    result, forcing_text = _compute_particular_integral(
        coefficients, request.forcing
    )

    payload = serialize(result)
    payload["forcing"] = forcing_text

    return success(payload)


@router.post("/complete-solution", summary="Solve F(D)y = X for y = CF + PI")
def complete_solution_endpoint(request: ParticularIntegralRequest):
    coefficients = solve("Reading coefficients", _exact_coefficients, request.coefficients)

    auxiliary, roots, cf = solve(
        "Computing the complementary function",
        complementary_function, coefficients
    )

    pi_result, forcing_text = _compute_particular_integral(
        coefficients, request.forcing
    )

    result = solve(
        "Building the complete solution",
        build_complete_solution,
        coefficients, cf, pi_result["pi"], forcing_text
    )

    return success({
        "auxiliary_equation": serialize(auxiliary),
        "roots": [
            {"root": serialize(root), "multiplicity": int(multiplicity)}
            for root, multiplicity in roots.items()
        ],
        "forcing": forcing_text,
        "complementary_function": serialize(result["cf"]),
        "particular_integral": serialize(result["pi"]),
        "complete_solution": serialize(result["complete_solution"]),
        "verification": {
            "cf": serialize(result["cf_verification"]),
            "pi": serialize(result["pi_verification"]),
            "complete": serialize(result["complete_verification"]),
            "all_verified": bool(
                result["cf_verification"]["verified"]
                and result["pi_verification"]["verified"]
                and result["complete_verification"]["verified"]
            )
        }
    })


class FirstOrderRequest(BaseModel):
    method: Literal[
        "variable_separable",
        "linear",
        "bernoulli",
        "exact"
    ]

    # variable_separable: dy/dx = f(x) g(y)
    f_x: Optional[str] = Field(default=None, max_length=300)
    g_y: Optional[str] = Field(default=None, max_length=300)

    # linear / bernoulli: dy/dx + P(x) y = Q(x) [y^n]
    P: Optional[str] = Field(default=None, max_length=300)
    Q: Optional[str] = Field(default=None, max_length=300)
    # The Bernoulli exponent. Bounded because it becomes an exponent in
    # the substitution v = y^(1-n); a huge value is never a real problem
    # and makes the algebra explode.
    n: Optional[float] = number("Bernoulli exponent n", default=None,
                                ge=-50, le=50)

    # exact: M dx + N dy = 0
    M: Optional[str] = Field(default=None, max_length=300)
    N: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def check_fields(self):
        required = {
            "variable_separable": ("f_x", "g_y"),
            "linear": ("P", "Q"),
            "bernoulli": ("P", "Q", "n"),
            "exact": ("M", "N")
        }[self.method]

        missing = [
            name for name in required
            if getattr(self, name) in (None, "")
        ]

        if missing:
            raise ValueError(
                f"method '{self.method}' requires: {', '.join(missing)}"
            )

        return self


@router.post("/first-order", summary="Solve a first-order ODE")
def first_order(request: FirstOrderRequest):
    if request.method == "variable_separable":
        result = solve(
            "Separating variables",
            variable_separable, request.f_x, request.g_y
        )

    elif request.method == "linear":
        result = solve(
            "Applying the integrating factor",
            linear_differential_equation, request.P, request.Q
        )

    elif request.method == "bernoulli":
        result = solve(
            "Solving Bernoulli's equation",
            bernoulli_equation, request.P, request.Q,
            sp.Rational(str(request.n))
        )

    else:
        result = solve(
            "Testing exactness and integrating",
            exact_equation, request.M, request.N
        )

    payload = serialize(result)
    payload["method"] = request.method

    return success(payload)
