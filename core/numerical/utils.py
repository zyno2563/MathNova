import sympy as sp

from core.safe_parser import parse_math


x = sp.symbols("x", real=True)


def parse_expression(expression):
    """
    Convert a user-entered expression in x into a
    SymPy expression.
    """

    expression = expression.replace("^", "**")

    allowed_functions = {
        "x": x,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "exp": sp.exp,
        "log": sp.log,
        "sqrt": sp.sqrt,
        "abs": sp.Abs,
        "pi": sp.pi,
        "e": sp.E,
        "E": sp.E
    }

    return parse_math(
        expression,
        locals=allowed_functions
    )


def lambdify_expression(expression):
    """
    Convert a SymPy expression in x into a fast
    NumPy-backed numerical function.
    """

    return sp.lambdify(
        x,
        expression,
        modules=["numpy"]
    )


def parse_matrix_text(matrix_text):
    """
    Convert a text block (rows separated by newlines,
    values separated by commas) into a list of lists
    of floats.

    Example:
        4, 1, 2
        3, 5, 1
        1, 1, 3
    """

    rows = []

    for line in matrix_text.strip().splitlines():

        if not line.strip():
            continue

        rows.append([
            float(value.strip())
            for value in line.split(",")
        ])

    if not rows:
        raise ValueError("Matrix cannot be empty.")

    column_count = len(rows[0])

    if any(len(row) != column_count for row in rows):
        raise ValueError(
            "All matrix rows must have the same "
            "number of columns."
        )

    return rows


def parse_values_text(values_text):
    """
    Convert a comma-separated text line into a list of
    floats. Used for vectors b, and for x/y data points
    in interpolation.
    """

    values = [
        float(value.strip())
        for value in values_text.split(",")
        if value.strip()
    ]

    if not values:
        raise ValueError("Values cannot be empty.")

    return values
