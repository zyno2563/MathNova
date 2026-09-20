import sympy as sp


x = sp.symbols("x")


def parse_function(expression):
    """
    Convert a mathematical expression entered by the user
    into a numerical Python function.
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

    symbolic_expression = sp.sympify(
        expression,
        locals=allowed_functions
    )

    return sp.lambdify(
        x,
        symbolic_expression,
        modules=["numpy"]
    )