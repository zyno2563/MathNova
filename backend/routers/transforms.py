"""
Laplace, Fourier and Z-transform endpoints (core.transforms.*).

Each transform family gets a forward endpoint, an inverse endpoint,
and a properties endpoint covering the standard shifting rules.
"""

from typing import Literal, Optional

import sympy as sp
from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from backend.errors import solve
from backend.limits import number
from backend.serialization import serialize, success
from core.transforms.fourier_transform import (
    fourier_cosine_transform,
    fourier_sine_transform,
    fourier_transform,
    inverse_fourier_cosine_transform,
    inverse_fourier_sine_transform,
    inverse_fourier_transform,
)
from core.transforms.fourier_transform import (
    scaling_property as fourier_scaling_property,
)
from core.transforms.fourier_transform import (
    shifting_property as fourier_shifting_property,
)
from core.transforms.laplace import (
    derivative_property,
    division_by_t,
    first_shifting_theorem,
    integral_property,
    inverse_laplace_transform,
    laplace_transform,
    multiplication_by_t,
    second_shifting_theorem,
)
from core.transforms.z_transform import (
    final_value_theorem,
    initial_value_theorem,
    inverse_z_transform,
    linearity_property,
    scaling_theorem,
    time_shifting_theorem,
    z_transform,
)

router = APIRouter(prefix="/transforms", tags=["transforms"])

FUNCTION = Field(..., min_length=1, max_length=300)


def exact(value):
    """
    Turn a JSON number into an exact SymPy value.

    JSON has no integer/float distinction that survives a float field,
    so a shift of 3 would otherwise print as (s - 3.0). Rational(str(x))
    keeps results in the closed form a textbook would show.
    """

    if value is None:
        return None

    return sp.Rational(str(value))


# =========================================================
# LAPLACE
# =========================================================

class LaplaceRequest(BaseModel):
    function: str = Field(
        ..., min_length=1, max_length=300,
        description="f(t)", examples=["sin(t)"]
    )


class InverseLaplaceRequest(BaseModel):
    function: str = Field(
        ..., min_length=1, max_length=300,
        description="F(s)", examples=["1/(s^2+1)"]
    )


class LaplacePropertyRequest(BaseModel):
    property: Literal[
        "first_shifting",
        "second_shifting",
        "derivative",
        "integral",
        "multiplication_by_t",
        "division_by_t"
    ]
    function: str = Field(
        ..., min_length=1, max_length=300, description="f(t)"
    )
    a: Optional[float] = number(
        "Shift a, for the shifting theorems", default=None
    )
    order: int = Field(
        default=1, ge=1, le=2, description="Derivative order (1 or 2)"
    )
    power: int = Field(
        default=1, ge=1, le=5, description="n in t^n f(t)"
    )

    @model_validator(mode="after")
    def check_fields(self):
        if self.property in ("first_shifting", "second_shifting") and self.a is None:
            raise ValueError(f"a is required for '{self.property}'")
        return self


@router.post("/laplace", summary="Laplace transform of f(t)")
def laplace(request: LaplaceRequest):
    result = solve(
        "Computing the Laplace transform",
        laplace_transform, request.function
    )
    return success(serialize(result))


@router.post("/laplace/inverse", summary="Inverse Laplace transform of F(s)")
def laplace_inverse(request: InverseLaplaceRequest):
    result = solve(
        "Computing the inverse Laplace transform",
        inverse_laplace_transform, request.function
    )
    return success(serialize(result))


@router.post("/laplace/property", summary="Apply a Laplace transform property")
def laplace_property(request: LaplacePropertyRequest):
    if request.property == "first_shifting":
        result = solve(
            "Applying the first shifting theorem",
            first_shifting_theorem, request.function, exact(request.a)
        )

    elif request.property == "second_shifting":
        result = solve(
            "Applying the second shifting theorem",
            second_shifting_theorem, request.function, exact(request.a)
        )

    elif request.property == "derivative":
        result = solve(
            "Applying the derivative property",
            derivative_property, request.function, request.order
        )

    elif request.property == "integral":
        result = solve(
            "Applying the integral property",
            integral_property, request.function
        )

    elif request.property == "multiplication_by_t":
        result = solve(
            "Applying multiplication by t^n",
            multiplication_by_t, request.function, request.power
        )

    else:
        result = solve(
            "Applying division by t",
            division_by_t, request.function
        )

    payload = serialize(result)
    payload["property"] = request.property

    return success(payload)


# =========================================================
# FOURIER
# =========================================================

class FourierRequest(BaseModel):
    kind: Literal["complex", "sine", "cosine"] = "complex"
    direction: Literal["forward", "inverse"] = "forward"
    function: str = Field(
        ..., min_length=1, max_length=300,
        description="f(x) for forward, F(w) for inverse",
        examples=["exp(-x^2)"]
    )


class FourierPropertyRequest(BaseModel):
    property: Literal["shifting", "scaling"]
    function: str = Field(..., min_length=1, max_length=300, description="f(x)")
    a: float = number("Shift or scale factor a")


@router.post("/fourier", summary="Fourier transform (complex, sine or cosine)")
def fourier(request: FourierRequest):
    engines = {
        ("complex", "forward"): fourier_transform,
        ("complex", "inverse"): inverse_fourier_transform,
        ("sine", "forward"): fourier_sine_transform,
        ("sine", "inverse"): inverse_fourier_sine_transform,
        ("cosine", "forward"): fourier_cosine_transform,
        ("cosine", "inverse"): inverse_fourier_cosine_transform
    }

    result = solve(
        "Computing the Fourier transform",
        engines[(request.kind, request.direction)], request.function
    )

    payload = serialize(result)
    payload["kind"] = request.kind
    payload["direction"] = request.direction

    return success(payload)


@router.post("/fourier/property", summary="Apply a Fourier transform property")
def fourier_property(request: FourierPropertyRequest):
    engine = (
        fourier_shifting_property if request.property == "shifting"
        else fourier_scaling_property
    )

    result = solve(
        f"Applying the {request.property} property",
        engine, request.function, exact(request.a)
    )

    payload = serialize(result)
    payload["property"] = request.property

    return success(payload)


# =========================================================
# Z-TRANSFORM
# =========================================================

class ZRequest(BaseModel):
    sequence: str = Field(
        ..., min_length=1, max_length=300,
        description="x(n)", examples=["a^n"]
    )


class InverseZRequest(BaseModel):
    function: str = Field(
        ..., min_length=1, max_length=300,
        description="X(z)", examples=["z/((z-1)*(z-2))"]
    )


class ZPropertyRequest(BaseModel):
    property: Literal[
        "linearity", "scaling", "time_shifting",
        "initial_value", "final_value"
    ]
    sequence: Optional[str] = Field(default=None, max_length=300)
    sequence_2: Optional[str] = Field(default=None, max_length=300)
    function: Optional[str] = Field(
        default=None, max_length=300, description="X(z), for the value theorems"
    )
    a: Optional[float] = number(default=None)
    b: Optional[float] = number(default=None)
    k: Optional[int] = Field(default=None, ge=0, le=20)

    @model_validator(mode="after")
    def check_fields(self):
        if self.property == "linearity":
            missing = [
                name for name in ("sequence", "sequence_2", "a", "b")
                if getattr(self, name) is None
            ]
        elif self.property == "scaling":
            missing = [
                name for name in ("sequence", "a")
                if getattr(self, name) is None
            ]
        elif self.property == "time_shifting":
            missing = [
                name for name in ("sequence", "k")
                if getattr(self, name) is None
            ]
        else:
            missing = ["function"] if not self.function else []

        if missing:
            raise ValueError(
                f"property '{self.property}' requires: {', '.join(missing)}"
            )

        return self


@router.post("/z", summary="Z-transform of x(n)")
def z(request: ZRequest):
    result = solve("Computing the Z-transform", z_transform, request.sequence)
    return success(serialize(result))


@router.post("/z/inverse", summary="Inverse Z-transform of X(z)")
def z_inverse(request: InverseZRequest):
    result = solve(
        "Computing the inverse Z-transform",
        inverse_z_transform, request.function
    )
    return success(serialize(result))


@router.post("/z/property", summary="Apply a Z-transform property")
def z_property(request: ZPropertyRequest):
    if request.property == "linearity":
        result = solve(
            "Applying linearity",
            linearity_property,
            request.sequence, request.sequence_2, exact(request.a), exact(request.b)
        )

    elif request.property == "scaling":
        result = solve(
            "Applying the scaling theorem",
            scaling_theorem, request.sequence, exact(request.a)
        )

    elif request.property == "time_shifting":
        result = solve(
            "Applying the time-shifting theorem",
            time_shifting_theorem, request.sequence, request.k
        )

    elif request.property == "initial_value":
        result = solve(
            "Applying the initial value theorem",
            initial_value_theorem, request.function
        )

    else:
        result = solve(
            "Applying the final value theorem",
            final_value_theorem, request.function
        )

    payload = serialize(result)
    payload["property"] = request.property

    return success(payload)
