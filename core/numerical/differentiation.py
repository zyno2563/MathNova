import sympy as sp

from core.numerical.utils import (
    x,
    parse_expression,
    lambdify_expression
)


def _verify_derivative(exact_value, approx_value, h):
    """
    Compare a finite-difference approximation against the
    exact symbolic derivative. The tolerance scales with
    the step size, since truncation error grows with h.
    """

    return abs(approx_value - exact_value) < max(
        100 * h,
        1e-4
    )


def forward_difference(function_expression, x0, h=1e-5):
    """
    Approximate f'(x0) using the forward difference
    formula:

        f'(x0) ~= (f(x0 + h) - f(x0)) / h
    """

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    x0 = float(x0)
    h = float(h)

    approx = (f(x0 + h) - f(x0)) / h

    exact = float(
        sp.diff(f_expr, x).subs(x, x0)
    )

    return {
        "function": f_expr,
        "x0": x0,
        "h": h,
        "approx_derivative": approx,
        "exact_derivative": exact,
        "verified": _verify_derivative(exact, approx, h)
    }


def backward_difference(function_expression, x0, h=1e-5):
    """
    Approximate f'(x0) using the backward difference
    formula:

        f'(x0) ~= (f(x0) - f(x0 - h)) / h
    """

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    x0 = float(x0)
    h = float(h)

    approx = (f(x0) - f(x0 - h)) / h

    exact = float(
        sp.diff(f_expr, x).subs(x, x0)
    )

    return {
        "function": f_expr,
        "x0": x0,
        "h": h,
        "approx_derivative": approx,
        "exact_derivative": exact,
        "verified": _verify_derivative(exact, approx, h)
    }


def central_difference(function_expression, x0, h=1e-5):
    """
    Approximate f'(x0) using the central difference
    formula:

        f'(x0) ~= (f(x0 + h) - f(x0 - h)) / (2h)
    """

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    x0 = float(x0)
    h = float(h)

    approx = (f(x0 + h) - f(x0 - h)) / (2 * h)

    exact = float(
        sp.diff(f_expr, x).subs(x, x0)
    )

    return {
        "function": f_expr,
        "x0": x0,
        "h": h,
        "approx_derivative": approx,
        "exact_derivative": exact,
        "verified": _verify_derivative(exact, approx, h)
    }


def second_derivative_central(function_expression, x0, h=1e-4):
    """
    Approximate f''(x0) using the central difference
    formula:

        f''(x0) ~= (f(x0+h) - 2 f(x0) + f(x0-h)) / h^2
    """

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    x0 = float(x0)
    h = float(h)

    approx = (
        f(x0 + h) - 2 * f(x0) + f(x0 - h)
    ) / h ** 2

    exact = float(
        sp.diff(f_expr, x, 2).subs(x, x0)
    )

    return {
        "function": f_expr,
        "x0": x0,
        "h": h,
        "approx_second_derivative": approx,
        "exact_second_derivative": exact,
        "verified": _verify_derivative(exact, approx, h)
    }
