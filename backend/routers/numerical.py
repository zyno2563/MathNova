"""Numerical methods endpoints (core.numerical.*)."""

from typing import List, Literal, Optional, Union

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from backend.errors import InvalidInput, solve
from backend.limits import MAX_POINTS, number
from backend.serialization import serialize, success
from core.numerical.differentiation import (
    backward_difference,
    central_difference,
    forward_difference,
    second_derivative_central,
)
from core.numerical.integration import (
    simpsons_one_third_rule,
    simpsons_three_eighth_rule,
    trapezoidal_rule,
)
from core.numerical.interpolation import (
    lagrange_interpolation,
    newton_divided_difference,
)
from core.numerical.linear_systems import (
    gauss_elimination,
    gauss_seidel,
    jacobi_iteration,
)
from core.numerical.root_finding import bisection, newton_raphson, secant
from core.numerical.utils import parse_matrix_text, parse_values_text

router = APIRouter(prefix="/numerical", tags=["numerical"])

FUNCTION = Field(
    ...,
    min_length=1,
    max_length=300,
    description="f(x)",
    examples=["x^3 - x - 2"]
)
TOLERANCE = Field(default=1e-6, gt=0, le=1.0)
MAX_ITERATIONS = Field(default=100, ge=1, le=1000)


class RootFindingRequest(BaseModel):
    method: Literal["bisection", "newton_raphson", "secant"]
    function: str = FUNCTION

    a: Optional[float] = number("Bracket start (bisection)", default=None)
    b: Optional[float] = number("Bracket end (bisection)", default=None)
    initial_guess: Optional[float] = number("x0 (Newton-Raphson)", default=None)
    x0: Optional[float] = number("First point (secant)", default=None)
    x1: Optional[float] = number("Second point (secant)", default=None)

    tolerance: float = TOLERANCE
    max_iterations: int = MAX_ITERATIONS

    @model_validator(mode="after")
    def check_fields(self):
        required = {
            "bisection": ("a", "b"),
            "newton_raphson": ("initial_guess",),
            "secant": ("x0", "x1")
        }[self.method]

        missing = [name for name in required if getattr(self, name) is None]

        if missing:
            raise ValueError(
                f"method '{self.method}' requires: {', '.join(missing)}"
            )

        return self


class DifferentiationRequest(BaseModel):
    method: Literal["forward", "backward", "central", "second_central"] = "central"
    function: str = FUNCTION
    x0: float = number("Point at which to differentiate")
    h: float = Field(default=1e-5, gt=0, le=1.0, description="Step size")


class IntegrationRequest(BaseModel):
    rule: Literal["trapezoidal", "simpson_1_3", "simpson_3_8"] = "simpson_1_3"
    function: str = FUNCTION
    a: float = number("Lower limit")
    b: float = number("Upper limit")
    n: int = Field(default=10, ge=1, le=1000, description="Subintervals")


class InterpolationRequest(BaseModel):
    method: Literal["lagrange", "newton_divided_difference"] = "lagrange"
    x_values: Union[str, List[float]] = Field(
        ..., max_length=4000, description="Comma-separated text or a list",
        examples=["0, 1, 2, 3"]
    )
    y_values: Union[str, List[float]] = Field(
        ..., max_length=4000, description="Comma-separated text or a list",
        examples=["1, 2, 9, 28"]
    )
    x_eval: Optional[float] = number(
        "Optional point to evaluate P(x) at", default=None
    )


class LinearSystemRequest(BaseModel):
    method: Literal["gauss_elimination", "jacobi", "gauss_seidel"] = "gauss_elimination"
    matrix: Union[str, List[List[float]]] = Field(
        ...,
        max_length=4000,
        description="Coefficient matrix A as text rows or nested lists",
        examples=["4, 1, 2\n3, 5, 1\n1, 1, 3"]
    )
    vector: Union[str, List[float]] = Field(
        ..., max_length=1000, description="Right-hand side b",
        examples=["4, 7, 3"]
    )
    tolerance: float = TOLERANCE
    max_iterations: int = MAX_ITERATIONS


def _bounded(values, label):
    """
    Cap a parsed series.

    Interpolation builds a symbolic polynomial through every point, so
    cost grows quadratically; a few hundred points is already far past
    anything a textbook problem uses.
    """

    if len(values) > MAX_POINTS:
        raise InvalidInput(
            f"{label}: at most {MAX_POINTS} values are supported "
            f"({len(values)} given)."
        )

    return values


def _values(raw, label="The values"):
    if isinstance(raw, str):
        parsed = solve("Reading the values", parse_values_text, raw)
    else:
        parsed = [float(value) for value in raw]

    return _bounded(parsed, label)


def _matrix(raw):
    if isinstance(raw, str):
        parsed = solve("Reading the matrix", parse_matrix_text, raw)
    else:
        parsed = [[float(value) for value in row] for row in raw]

    _bounded(parsed, "The matrix")

    for row in parsed:
        _bounded(row, "Each matrix row")

    return parsed


@router.post("/root-finding", summary="Find a root of f(x) = 0")
def root_finding(request: RootFindingRequest):
    if request.method == "bisection":
        result = solve(
            "Running the bisection method",
            bisection, request.function, request.a, request.b,
            tolerance=request.tolerance,
            max_iterations=request.max_iterations
        )

    elif request.method == "newton_raphson":
        result = solve(
            "Running Newton-Raphson",
            newton_raphson, request.function, request.initial_guess,
            tolerance=request.tolerance,
            max_iterations=request.max_iterations
        )

    else:
        result = solve(
            "Running the secant method",
            secant, request.function, request.x0, request.x1,
            tolerance=request.tolerance,
            max_iterations=request.max_iterations
        )

    payload = serialize(result)
    payload["method"] = request.method

    return success(payload)


@router.post("/differentiation", summary="Differentiate f(x) numerically")
def differentiation(request: DifferentiationRequest):
    engines = {
        "forward": forward_difference,
        "backward": backward_difference,
        "central": central_difference,
        "second_central": second_derivative_central
    }

    result = solve(
        "Applying the finite-difference formula",
        engines[request.method], request.function, request.x0, request.h
    )

    payload = serialize(result)
    payload["method"] = request.method

    # Normalise the key names so the client does not have to know
    # that the second-derivative engine names its fields differently.
    if request.method == "second_central":
        payload["approximate"] = payload.get("approx_second_derivative")
        payload["exact"] = payload.get("exact_second_derivative")
    else:
        payload["approximate"] = payload.get("approx_derivative")
        payload["exact"] = payload.get("exact_derivative")

    return success(payload)


@router.post("/integration", summary="Integrate f(x) numerically")
def integration(request: IntegrationRequest):
    engines = {
        "trapezoidal": trapezoidal_rule,
        "simpson_1_3": simpsons_one_third_rule,
        "simpson_3_8": simpsons_three_eighth_rule
    }

    result = solve(
        "Applying the quadrature rule",
        engines[request.rule], request.function, request.a, request.b, request.n
    )

    payload = serialize(result)
    payload["rule"] = request.rule

    return success(payload)


@router.post("/interpolation", summary="Build an interpolating polynomial")
def interpolation(request: InterpolationRequest):
    x_values = _values(request.x_values)
    y_values = _values(request.y_values)

    if len(x_values) != len(y_values):
        raise InvalidInput(
            "x_values and y_values must have the same length."
        )

    if len(x_values) < 2:
        raise InvalidInput("At least two data points are required.")

    if len(x_values) > 25:
        raise InvalidInput("At most 25 data points are supported.")

    engine = (
        lagrange_interpolation if request.method == "lagrange"
        else newton_divided_difference
    )

    result = solve(
        "Building the interpolating polynomial",
        engine, x_values, y_values, request.x_eval
    )

    payload = serialize(result)
    payload["method"] = request.method
    payload["points"] = [
        {"x": x, "y": y} for x, y in zip(x_values, y_values)
    ]

    return success(payload)


@router.post("/linear-system", summary="Solve Ax = b numerically")
def linear_system(request: LinearSystemRequest):
    matrix = _matrix(request.matrix)
    vector = _values(request.vector)

    if len(matrix) != len(vector):
        raise InvalidInput(
            "The number of rows in A must match the length of b."
        )

    if len(vector) > 10:
        raise InvalidInput("At most a 10x10 system is supported.")

    if request.method == "gauss_elimination":
        result = solve(
            "Running Gaussian elimination",
            gauss_elimination, matrix, vector
        )

    elif request.method == "jacobi":
        result = solve(
            "Running Jacobi iteration",
            jacobi_iteration, matrix, vector,
            tolerance=request.tolerance,
            max_iterations=request.max_iterations
        )

    else:
        result = solve(
            "Running Gauss-Seidel iteration",
            gauss_seidel, matrix, vector,
            tolerance=request.tolerance,
            max_iterations=request.max_iterations
        )

    payload = serialize(result)
    payload["method"] = request.method

    return success(payload)
