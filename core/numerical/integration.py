import numpy as np
import sympy as sp

from core.numerical.utils import (
    x,
    parse_expression,
    lambdify_expression
)


def _verify_integral(exact_value, approx_value):
    """
    Compare a numerical quadrature result against the
    exact definite integral computed symbolically by
    SymPy. The tolerance is relatively loose since a
    coarse Trapezoidal rule (O(h^2)) carries more
    truncation error than Simpson's rules at the same n.
    """

    return abs(approx_value - exact_value) < max(
        5e-2 * max(abs(exact_value), 1),
        1e-3
    )


def _exact_integral(f_expr, a, b):
    try:
        return float(
            sp.integrate(f_expr, (x, a, b))
        )
    except Exception:
        return None


def trapezoidal_rule(function_expression, a, b, n=10):
    """
    Approximate the definite integral of f(x) over
    [a, b] using the Trapezoidal rule with n
    subintervals.
    """

    if n < 1:
        raise ValueError(
            "n must be at least 1."
        )

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    a = float(a)
    b = float(b)

    x_values = np.linspace(a, b, n + 1)
    y_values = f(x_values)

    h = (b - a) / n

    integral = h / 2 * (
        y_values[0]
        + 2 * np.sum(y_values[1:-1])
        + y_values[-1]
    )

    integral = float(integral)

    exact = _exact_integral(f_expr, a, b)

    verified = (
        _verify_integral(exact, integral)
        if exact is not None else False
    )

    return {
        "function": f_expr,
        "a": a,
        "b": b,
        "n": n,
        "x_values": x_values.tolist(),
        "y_values": y_values.tolist(),
        "integral": integral,
        "exact_integral": exact,
        "verified": verified
    }


def simpsons_one_third_rule(function_expression, a, b, n=10):
    """
    Approximate the definite integral of f(x) over
    [a, b] using Simpson's 1/3 rule.

    n (the number of subintervals) must be even.
    """

    if n < 2 or n % 2 != 0:
        raise ValueError(
            "n must be a positive even number."
        )

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    a = float(a)
    b = float(b)

    x_values = np.linspace(a, b, n + 1)
    y_values = f(x_values)

    h = (b - a) / n

    integral = h / 3 * (
        y_values[0]
        + y_values[-1]
        + 4 * np.sum(y_values[1:-1:2])
        + 2 * np.sum(y_values[2:-1:2])
    )

    integral = float(integral)

    exact = _exact_integral(f_expr, a, b)

    verified = (
        _verify_integral(exact, integral)
        if exact is not None else False
    )

    return {
        "function": f_expr,
        "a": a,
        "b": b,
        "n": n,
        "x_values": x_values.tolist(),
        "y_values": y_values.tolist(),
        "integral": integral,
        "exact_integral": exact,
        "verified": verified
    }


def simpsons_three_eighth_rule(function_expression, a, b, n=9):
    """
    Approximate the definite integral of f(x) over
    [a, b] using Simpson's 3/8 rule.

    n (the number of subintervals) must be a multiple
    of 3.
    """

    if n < 3 or n % 3 != 0:
        raise ValueError(
            "n must be a positive multiple of 3."
        )

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    a = float(a)
    b = float(b)

    x_values = np.linspace(a, b, n + 1)
    y_values = f(x_values)

    h = (b - a) / n

    multiple_of_three_sum = np.sum(
        y_values[3:-1:3]
    )

    other_sum = (
        np.sum(y_values[1:-1])
        - multiple_of_three_sum
    )

    integral = 3 * h / 8 * (
        y_values[0]
        + y_values[-1]
        + 3 * other_sum
        + 2 * multiple_of_three_sum
    )

    integral = float(integral)

    exact = _exact_integral(f_expr, a, b)

    verified = (
        _verify_integral(exact, integral)
        if exact is not None else False
    )

    return {
        "function": f_expr,
        "a": a,
        "b": b,
        "n": n,
        "x_values": x_values.tolist(),
        "y_values": y_values.tolist(),
        "integral": integral,
        "exact_integral": exact,
        "verified": verified
    }
