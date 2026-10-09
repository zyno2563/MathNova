import sympy as sp

from core.safe_parser import parse_math


x = sp.symbols("x")


def parse_symbolic_function(expression):
    """
    Parse f(x) into a picklable expression, suitable for guarded execution.
    """

    expression = expression.replace("^", "**")

    allowed_functions = {
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


def function_from_expression(symbolic_expression):
    """Build a numerical function from an already validated expression."""
    return sp.lambdify(
        x,
        symbolic_expression,
        modules=["numpy"]
    )


def parse_function(expression):
    """Convert a public math expression into a numerical function."""
    return function_from_expression(parse_symbolic_function(expression))
