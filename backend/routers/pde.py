"""First-order partial differential equation endpoints (core.pde.first_order)."""

from typing import List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from backend.errors import solve
from backend.serialization import serialize, success
from core.pde.first_order import (
    eliminate_arbitrary_constants,
    lagrange_linear_pde,
    standard_type_1,
    standard_type_2_clairaut,
    standard_type_3_separable,
    standard_type_4_no_xy,
)

router = APIRouter(prefix="/pde", tags=["pde"])


class FormationRequest(BaseModel):
    z: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="z = f(x, y; constants)",
        examples=["a*x + a^2*y^2 + b"]
    )
    constants: List[str] = Field(
        ...,
        max_length=2,
        description="Arbitrary constants to eliminate (one or two)",
        examples=[["a", "b"]]
    )

    @model_validator(mode="after")
    def check_constants(self):
        if len(self.constants) not in (1, 2):
            raise ValueError(
                "Provide exactly one or two arbitrary constants"
            )

        for name in self.constants:
            if not name.strip():
                raise ValueError("Constant names cannot be blank")

            if len(name) > 20:
                raise ValueError(
                    "Constant names must be at most 20 characters"
                )

        return self


class LagrangeRequest(BaseModel):
    P: str = Field(..., min_length=1, max_length=300, examples=["y*z"])
    Q: str = Field(..., min_length=1, max_length=300, examples=["x*z"])
    R: str = Field(..., min_length=1, max_length=300, examples=["x*y"])


class StandardTypeRequest(BaseModel):
    type: Literal["type_1", "clairaut", "separable", "no_xy"]

    f: Optional[str] = Field(
        default=None,
        max_length=300,
        description="f(p,q), f(x,p) or f(z,p,q) depending on the type"
    )
    g: Optional[str] = Field(
        default=None,
        max_length=300,
        description="g(y,q), only for the separable type"
    )

    @model_validator(mode="after")
    def check_fields(self):
        if not self.f:
            raise ValueError("f is required")

        if self.type == "separable" and not self.g:
            raise ValueError("g is required for the separable type")

        return self


@router.post("/formation", summary="Form a PDE by eliminating constants")
def formation(request: FormationRequest):
    result = solve(
        "Eliminating the arbitrary constants",
        eliminate_arbitrary_constants, request.z, request.constants
    )

    return success(serialize(result))


@router.post("/lagrange", summary="Solve Lagrange's linear PDE Pp + Qq = R")
def lagrange(request: LagrangeRequest):
    result = solve(
        "Solving the subsidiary equations",
        lagrange_linear_pde, request.P, request.Q, request.R
    )

    return success(serialize(result))


@router.post("/standard-type", summary="Solve a standard first-order PDE type")
def standard_type(request: StandardTypeRequest):
    if request.type == "type_1":
        result = solve(
            "Solving f(p, q) = 0", standard_type_1, request.f
        )

    elif request.type == "clairaut":
        result = solve(
            "Solving Clairaut's equation",
            standard_type_2_clairaut, request.f
        )

    elif request.type == "separable":
        result = solve(
            "Separating f(x, p) = g(y, q)",
            standard_type_3_separable, request.f, request.g
        )

    else:
        result = solve(
            "Solving f(z, p, q) = 0", standard_type_4_no_xy, request.f
        )

    payload = serialize(result)
    payload["type"] = request.type

    return success(payload)
