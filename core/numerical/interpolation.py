import sympy as sp

from core.safe_parser import parse_math

from core.numerical.utils import x


def _to_exact(value):
    """
    Convert a Python int/float into an exact SymPy
    Rational, avoiding the tiny binary floating-point
    noise that would otherwise contaminate symbolic
    verification (e.g. plain 1.77e-15 residual terms).
    """

    if isinstance(value, (int, sp.Integer, sp.Rational)):
        return parse_math(value)

    return sp.Rational(str(value))


def _verify_interpolation(polynomial, x_values, y_values):
    """
    Check that the interpolating polynomial passes
    through every given data point.
    """

    for x_value, y_value in zip(x_values, y_values):

        difference = sp.simplify(
            polynomial.subs(x, x_value) - y_value
        )

        if difference != 0 and abs(
            complex(difference)
        ) > 1e-9:
            return False

    return True


def lagrange_interpolation(x_values, y_values, x_eval=None):
    """
    Build the Lagrange interpolating polynomial through
    the given (x, y) data points:

        P(x) = sum_i y_i * L_i(x)

    where:

        L_i(x) = prod_(j != i) (x - x_j) / (x_i - x_j)
    """

    if len(x_values) != len(y_values):
        raise ValueError(
            "x_values and y_values must have the same "
            "length."
        )

    if len(set(x_values)) != len(x_values):
        raise ValueError(
            "x_values must all be distinct."
        )

    x_values = [_to_exact(value) for value in x_values]
    y_values = [_to_exact(value) for value in y_values]

    n = len(x_values)

    polynomial = sp.Integer(0)

    for i in range(n):

        term = y_values[i]

        for j in range(n):

            if j == i:
                continue

            term *= (
                (x - x_values[j])
                / (x_values[i] - x_values[j])
            )

        polynomial += term

    polynomial = sp.expand(polynomial)

    result = {
        "polynomial": polynomial,
        "verified": _verify_interpolation(
            polynomial,
            x_values,
            y_values
        )
    }

    if x_eval is not None:

        result["x_eval"] = x_eval

        result["y_eval"] = float(
            polynomial.subs(x, x_eval)
        )

    return result


def newton_divided_difference(x_values, y_values, x_eval=None):
    """
    Build Newton's divided-difference interpolating
    polynomial through the given (x, y) data points:

        P(x) = f[x0] + f[x0,x1](x - x0)
               + f[x0,x1,x2](x - x0)(x - x1) + ...
    """

    if len(x_values) != len(y_values):
        raise ValueError(
            "x_values and y_values must have the same "
            "length."
        )

    if len(set(x_values)) != len(x_values):
        raise ValueError(
            "x_values must all be distinct."
        )

    x_values = [_to_exact(value) for value in x_values]
    y_values = [_to_exact(value) for value in y_values]

    n = len(x_values)

    table = [list(y_values)]

    for level in range(1, n):

        previous_level = table[-1]

        new_level = []

        for i in range(n - level):

            numerator = (
                previous_level[i + 1]
                - previous_level[i]
            )

            denominator = (
                x_values[i + level]
                - x_values[i]
            )

            new_level.append(
                sp.simplify(numerator / denominator)
            )

        table.append(new_level)

    coefficients = [level[0] for level in table]

    polynomial = coefficients[0]

    product_term = sp.Integer(1)

    for i in range(1, n):

        product_term *= (x - x_values[i - 1])

        polynomial += coefficients[i] * product_term

    polynomial = sp.expand(polynomial)

    result = {
        "divided_difference_table": table,
        "coefficients": coefficients,
        "polynomial": polynomial,
        "verified": _verify_interpolation(
            polynomial,
            x_values,
            y_values
        )
    }

    if x_eval is not None:

        result["x_eval"] = x_eval

        result["y_eval"] = float(
            polynomial.subs(x, x_eval)
        )

    return result
