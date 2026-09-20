"""
Conversion of engine results into JSON-safe payloads.

The core/ engines return SymPy expressions, NumPy scalars, and
nested dicts/lists of those. Routers stay thin by handing whatever
an engine returned straight to `serialize()`.
"""

import math

import numpy as np
import sympy as sp


def success(result, **extra):
    """Wrap an engine result in the API's success envelope."""

    payload = {"ok": True, "result": serialize(result)}
    payload.update(extra)

    return payload


def as_math(expression):
    """
    Represent a single SymPy object in both plain text and LaTeX,
    so the frontend can render it with KaTeX and still show a
    copyable source form.
    """

    return {
        "text": sp.sstr(expression),
        "latex": sp.latex(expression)
    }


def as_number(value):
    """
    Convert a numeric value to a JSON-safe float.

    JSON has no representation for NaN or +/-Infinity, so those
    become None rather than producing a payload that json.dumps
    emits but strict JSON parsers reject.
    """

    number = float(value)

    if math.isnan(number) or math.isinf(number):
        return None

    return number


def serialize(value):
    """
    Recursively convert an engine result into JSON-safe data.

    SymPy objects become {"text": ..., "latex": ...}; NumPy scalars
    and arrays become plain Python numbers and lists; dicts and
    sequences are walked; everything else is passed through.
    """

    # Order matters: bool is a subclass of int, and SymPy Booleans
    # must be caught before the generic Basic branch below.
    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if value is None or isinstance(value, str):
        return value

    if isinstance(value, sp.logic.boolalg.BooleanAtom):
        return bool(value)

    if isinstance(value, (sp.Matrix, sp.ImmutableMatrix)):
        return {
            "text": sp.sstr(value),
            "latex": sp.latex(value),
            "rows": value.rows,
            "cols": value.cols,
            "entries": [
                [as_math(entry) for entry in value.row(row_index)]
                for row_index in range(value.rows)
            ]
        }

    if isinstance(value, sp.Basic):
        # A SymPy number that is exactly representable stays useful
        # to the frontend as a plain number as well.
        if value.is_number and value.is_real and value.is_finite:
            return {
                **as_math(value),
                "value": as_number(value.evalf())
            }

        return as_math(value)

    if isinstance(value, np.ndarray):
        return [serialize(item) for item in value.tolist()]

    if isinstance(value, np.generic):
        return serialize(value.item())

    if isinstance(value, (int,)):
        return value

    if isinstance(value, float):
        return as_number(value)

    if isinstance(value, dict):
        return {
            str(key): serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serialize(item) for item in value]

    return str(value)
