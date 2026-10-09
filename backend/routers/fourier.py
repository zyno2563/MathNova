"""Fourier series endpoints (core.fourier.series)."""

import math

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.errors import InvalidInput, solve
from backend.serialization import as_number, success
from core.calculus.parser import function_from_expression, parse_symbolic_function
from core.fourier.series import (
    calculate_absolute_error,
    calculate_coefficients,
    evaluate_series,
)

router = APIRouter(prefix="/fourier", tags=["fourier-series"])


class SeriesRequest(BaseModel):
    expression: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="f(x) in terms of x, e.g. 'x' or 'x^2'",
        examples=["x"]
    )
    half_period: float = Field(
        default=math.pi,
        gt=0,
        le=1000,
        description="L, half of the period 2L"
    )
    terms: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of harmonics N"
    )
    points: int = Field(
        default=400,
        ge=20,
        le=2000,
        description="Samples used for the comparison curve"
    )


def _sample(function, x_values):
    """
    Evaluate f pointwise, tolerating points where it is undefined.

    The curve is for plotting, so a singular point becomes null
    rather than failing the whole request.
    """

    samples = []

    for value in x_values:
        try:
            samples.append(as_number(function(value)))
        except Exception:  # noqa: BLE001 - undefined at this point
            samples.append(None)

    return samples


@router.post("/series", summary="Expand f(x) as a Fourier series")
def fourier_series(request: SeriesRequest):
    # Symbolic parsing can simplify mathematical functions, so it needs
    # the same deadline as calculation. Only compiling the validated
    # expression stays in-process: a live callable cannot cross a pipe.
    expression = solve(
        "Parsing f(x)", parse_symbolic_function, request.expression
    )
    function = solve(
        "Preparing f(x)", function_from_expression, expression, isolated=False
    )

    # lambdify does not check that the result is
    # callable on a real number; fail early with a clear message.
    try:
        function(0.0)
    except Exception as error:  # noqa: BLE001
        raise InvalidInput(
            f"f(x) could not be evaluated at x = 0: {error}"
        )

    half_period = request.half_period

    a0, an, bn = solve(
        "Computing Fourier coefficients",
        calculate_coefficients,
        function,
        half_period,
        request.terms
    )

    x_values = np.linspace(
        -half_period, half_period, request.points
    ).tolist()

    original = _sample(function, x_values)

    approximation = [
        as_number(evaluate_series(value, half_period, a0, an, bn))
        for value in x_values
    ]

    # Report the error at a point that is representative rather than
    # at a jump discontinuity, matching the classic L/2 check.
    sample_point = half_period / 2
    exact_value = None
    error_value = None

    approximate_value = as_number(
        evaluate_series(sample_point, half_period, a0, an, bn)
    )

    try:
        exact_value = as_number(function(sample_point))
    except Exception:  # noqa: BLE001 - undefined at the sample point
        exact_value = None

    if exact_value is not None and approximate_value is not None:
        error_value = as_number(
            calculate_absolute_error(exact_value, approximate_value)
        )

    return success(
        {
            "expression": request.expression,
            "half_period": half_period,
            "terms": request.terms,
            "a0": as_number(a0),
            "an": [as_number(value) for value in an],
            "bn": [as_number(value) for value in bn],
            "harmonics": [
                {
                    "n": index + 1,
                    "an": as_number(an[index]),
                    "bn": as_number(bn[index])
                }
                for index in range(len(an))
            ],
            "plot": {
                "x": x_values,
                "original": original,
                "approximation": approximation
            },
            "accuracy": {
                "at_x": sample_point,
                "exact": exact_value,
                "approximation": approximate_value,
                "absolute_error": error_value
            }
        }
    )
