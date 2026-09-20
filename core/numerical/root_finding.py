import sympy as sp

from core.numerical.utils import (
    x,
    parse_expression,
    lambdify_expression
)


def _verify_root(f_expr, root, tolerance):
    """
    Independently verify a numerically found root by
    running SymPy's nsolve() (mpmath's findroot) starting
    from the root itself, and checking both methods agree.
    """

    try:
        refined_root = float(
            sp.nsolve(f_expr, x, root)
        )

        return abs(refined_root - root) < max(
            tolerance * 100,
            1e-4
        )

    except Exception:
        return False


def bisection(
    function_expression,
    a,
    b,
    tolerance=1e-6,
    max_iterations=100
):
    """
    Find a root of f(x) = 0 in [a, b] using the
    Bisection method.

    Requires f(a) and f(b) to have opposite signs.
    """

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    a = float(a)
    b = float(b)

    f_a = f(a)
    f_b = f(b)

    if f_a * f_b > 0:
        raise ValueError(
            "f(a) and f(b) must have opposite signs."
        )

    iterations = []

    c = a

    for iteration in range(1, max_iterations + 1):

        c = (a + b) / 2
        f_c = f(c)

        iterations.append({
            "iteration": iteration,
            "a": a,
            "b": b,
            "c": c,
            "f_c": f_c
        })

        if abs(f_c) < tolerance or (b - a) / 2 < tolerance:
            break

        if f_a * f_c < 0:
            b, f_b = c, f_c
        else:
            a, f_a = c, f_c

    else:
        raise ValueError(
            "Bisection method did not converge within "
            "the maximum number of iterations."
        )

    return {
        "function": f_expr,
        "root": c,
        "residual": f(c),
        "iterations": iterations,
        "iterations_count": len(iterations),
        "verified": _verify_root(f_expr, c, tolerance)
    }


def newton_raphson(
    function_expression,
    initial_guess,
    tolerance=1e-6,
    max_iterations=100
):
    """
    Find a root of f(x) = 0 using the Newton-Raphson
    method:

        x_(n+1) = x_n - f(x_n) / f'(x_n)
    """

    f_expr = parse_expression(function_expression)
    f_prime_expr = sp.diff(f_expr, x)

    f = lambdify_expression(f_expr)
    f_prime = lambdify_expression(f_prime_expr)

    x_current = float(initial_guess)

    iterations = []

    for iteration in range(1, max_iterations + 1):

        f_value = f(x_current)
        f_prime_value = f_prime(x_current)

        if f_prime_value == 0:
            raise ValueError(
                "Derivative is zero; Newton-Raphson "
                "cannot continue."
            )

        x_next = x_current - f_value / f_prime_value

        iterations.append({
            "iteration": iteration,
            "x": x_current,
            "f_x": f_value,
            "f_prime_x": f_prime_value,
            "x_next": x_next
        })

        if abs(x_next - x_current) < tolerance:
            x_current = x_next
            break

        x_current = x_next

    else:
        raise ValueError(
            "Newton-Raphson method did not converge "
            "within the maximum number of iterations."
        )

    return {
        "function": f_expr,
        "derivative": f_prime_expr,
        "root": x_current,
        "residual": f(x_current),
        "iterations": iterations,
        "iterations_count": len(iterations),
        "verified": _verify_root(
            f_expr,
            x_current,
            tolerance
        )
    }


def secant(
    function_expression,
    x0,
    x1,
    tolerance=1e-6,
    max_iterations=100
):
    """
    Find a root of f(x) = 0 using the Secant method:

        x_(n+1) = x_n - f(x_n)(x_n - x_(n-1))
                        / (f(x_n) - f(x_(n-1)))
    """

    f_expr = parse_expression(function_expression)
    f = lambdify_expression(f_expr)

    x_prev = float(x0)
    x_curr = float(x1)

    iterations = []

    for iteration in range(1, max_iterations + 1):

        f_prev = f(x_prev)
        f_curr = f(x_curr)

        if f_curr - f_prev == 0:
            raise ValueError(
                "Division by zero encountered; the "
                "Secant method cannot continue."
            )

        x_next = x_curr - f_curr * (
            (x_curr - x_prev) / (f_curr - f_prev)
        )

        iterations.append({
            "iteration": iteration,
            "x_prev": x_prev,
            "x_curr": x_curr,
            "f_curr": f_curr,
            "x_next": x_next
        })

        if abs(x_next - x_curr) < tolerance:
            x_curr = x_next
            break

        x_prev, x_curr = x_curr, x_next

    else:
        raise ValueError(
            "Secant method did not converge within the "
            "maximum number of iterations."
        )

    return {
        "function": f_expr,
        "root": x_curr,
        "residual": f(x_curr),
        "iterations": iterations,
        "iterations_count": len(iterations),
        "verified": _verify_root(f_expr, x_curr, tolerance)
    }
