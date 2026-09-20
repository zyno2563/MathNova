import sympy as sp


x = sp.symbols("x")


def parse_expression(expression):
    """
    Convert a user-entered mathematical expression
    into a SymPy expression.
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

    return sp.sympify(
        expression,
        locals=allowed_functions
    )


def differentiate(expression):
    """
    Calculate the derivative of an expression.
    """

    symbolic_expression = parse_expression(
        expression
    )

    return sp.diff(
        symbolic_expression,
        x
    )


def integrate(expression):
    """
    Calculate the indefinite integral of an expression.
    """

    symbolic_expression = parse_expression(
        expression
    )

    return sp.integrate(
        symbolic_expression,
        x
    )


def evaluate(expression, value):
    """
    Evaluate an expression at a given x value.
    """

    symbolic_expression = parse_expression(
        expression
    )

    result = symbolic_expression.subs(
        x,
        value
    )

    return result