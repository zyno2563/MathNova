"""Calculus endpoints (core.calculus.calculus)."""

import sympy as sp
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.errors import solve
from backend.limits import number
from backend.serialization import serialize, success
from core.calculus.calculus import differentiate, evaluate, integrate, parse_expression

router = APIRouter(prefix="/calculus", tags=["calculus"])

EXPRESSION = Field(
    ...,
    min_length=1,
    max_length=500,
    description="Expression in x, e.g. 'x^2 + sin(x)'",
    examples=["x^2 + sin(x)"]
)


class ExpressionRequest(BaseModel):
    expression: str = EXPRESSION


class EvaluateRequest(BaseModel):
    expression: str = EXPRESSION
    value: float = number("The x value to substitute")


@router.post("/differentiate", summary="Differentiate an expression")
def differentiate_expression(request: ExpressionRequest):
    original = solve("Parsing the expression", parse_expression, request.expression)
    derivative = solve("Differentiating", differentiate, request.expression)

    return success({
        "input": serialize(original),
        "derivative": serialize(derivative),
        "simplified": serialize(sp.simplify(derivative))
    })


@router.post("/integrate", summary="Integrate an expression")
def integrate_expression(request: ExpressionRequest):
    original = solve("Parsing the expression", parse_expression, request.expression)
    antiderivative = solve("Integrating", integrate, request.expression)

    return success({
        "input": serialize(original),
        "integral": serialize(antiderivative),
        # The engine returns an indefinite integral; show the
        # constant of integration the way a textbook would.
        "with_constant": serialize(antiderivative + sp.Symbol("C"))
    })


@router.post("/evaluate", summary="Evaluate an expression at a point")
def evaluate_expression(request: EvaluateRequest):
    # Substitute an exact value, not a float. JSON has no integer type
    # that survives a float field, so x = 3 arrived as 3.0 and SymPy
    # returned 10.0000000000000 for what the response calls the exact
    # value. Rational(str(x)) is the same convention the transforms
    # router already uses to keep results in closed form.
    at = sp.Rational(str(request.value))

    exact = solve("Evaluating", evaluate, request.expression, at)

    numeric = None

    try:
        numeric = float(sp.N(exact))
    except (TypeError, ValueError):
        numeric = None

    return success({
        "expression": request.expression,
        "at": request.value,
        "exact": serialize(exact),
        "numeric": numeric
    })
