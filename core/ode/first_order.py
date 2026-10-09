import sympy as sp

from core.safe_parser import parse_math


x, y = sp.symbols("x y", real=True)
C1 = sp.Symbol("C1")


def parse_expression(expression):
    """
    Convert a user-entered expression (in x and/or y)
    into a SymPy expression.
    """

    expression = expression.replace("^", "**")

    allowed_functions = {
        "x": x,
        "y": y,
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


def variable_separable(f_x_expression, g_y_expression):
    """
    Solve:

        dy/dx = f(x) * g(y)

    by separating variables:

        dy / g(y) = f(x) dx
    """

    f_x = parse_expression(f_x_expression)
    g_y = parse_expression(g_y_expression)

    lhs_integral = sp.integrate(1 / g_y, y)
    rhs_integral = sp.integrate(f_x, x) + C1

    solution = sp.Eq(lhs_integral, rhs_integral)

    verified = False

    try:
        implicit_form = lhs_integral - rhs_integral
        dydx = sp.idiff(implicit_form, y, x)
        verified = sp.simplify(dydx - f_x * g_y) == 0

    except Exception:
        verified = False

    return {
        "f_x": f_x,
        "g_y": g_y,
        "lhs_integral": lhs_integral,
        "rhs_integral": rhs_integral,
        "solution": solution,
        "verified": verified
    }


def linear_differential_equation(P_expression, Q_expression):
    """
    Solve:

        dy/dx + P(x) y = Q(x)

    using the integrating factor:

        IF = e^(int P dx)

        y * IF = int Q * IF dx + C
    """

    P = parse_expression(P_expression)
    Q = parse_expression(Q_expression)

    integrating_factor = sp.simplify(
        sp.exp(
            sp.integrate(P, x)
        )
    )

    rhs_integral = (
        sp.integrate(Q * integrating_factor, x)
        + C1
    )

    solution_y = sp.simplify(
        rhs_integral / integrating_factor
    )

    solution = sp.Eq(y, solution_y)

    verified = False

    try:
        derivative_check = sp.simplify(
            sp.diff(solution_y, x)
            + P * solution_y
            - Q
        )

        verified = derivative_check == 0

    except Exception:
        verified = False

    return {
        "P": P,
        "Q": Q,
        "integrating_factor": integrating_factor,
        "rhs_integral": rhs_integral,
        "solution": solution,
        "verified": verified
    }


def bernoulli_equation(P_expression, Q_expression, n_value):
    """
    Solve:

        dy/dx + P(x) y = Q(x) y^n

    using the substitution v = y^(1-n),
    which reduces the equation to the
    linear form:

        dv/dx + (1 - n) P(x) v = (1 - n) Q(x)
    """

    P = parse_expression(P_expression)
    Q = parse_expression(Q_expression)
    n = parse_math(n_value)

    if n == 1:
        raise ValueError(
            "n must not equal 1 "
            "(the equation reduces to a "
            "separable equation)."
        )

    linear_P = (1 - n) * P
    linear_Q = (1 - n) * Q

    integrating_factor = sp.simplify(
        sp.exp(
            sp.integrate(linear_P, x)
        )
    )

    rhs_integral = (
        sp.integrate(linear_Q * integrating_factor, x)
        + C1
    )

    v_solution = sp.simplify(
        rhs_integral / integrating_factor
    )

    solution = sp.Eq(
        y ** (1 - n),
        v_solution
    )

    verified = False

    try:
        y_explicit = sp.simplify(
            v_solution ** (1 / (1 - n))
        )

        derivative_check = sp.simplify(
            sp.diff(y_explicit, x)
            + P * y_explicit
            - Q * y_explicit ** n
        )

        verified = derivative_check == 0

    except Exception:
        verified = False

    return {
        "P": P,
        "Q": Q,
        "n": n,
        "linear_P": linear_P,
        "linear_Q": linear_Q,
        "integrating_factor": integrating_factor,
        "v_solution": v_solution,
        "solution": solution,
        "verified": verified
    }


def exact_equation(M_expression, N_expression):
    """
    Solve:

        M(x, y) dx + N(x, y) dy = 0

    Checks exactness (dM/dy = dN/dx) and, if
    exact, builds F(x, y) = C such that:

        dF/dx = M
        dF/dy = N
    """

    M = parse_expression(M_expression)
    N = parse_expression(N_expression)

    dM_dy = sp.diff(M, y)
    dN_dx = sp.diff(N, x)

    is_exact = sp.simplify(dM_dy - dN_dx) == 0

    if not is_exact:
        raise ValueError(
            "Equation is not exact: "
            "∂M/∂y ≠ ∂N/∂x."
        )

    F_partial = sp.integrate(M, x)

    g_prime = sp.simplify(
        N - sp.diff(F_partial, y)
    )

    g = sp.integrate(g_prime, y)

    F = sp.simplify(F_partial + g)

    solution = sp.Eq(F, C1)

    verified = False

    try:
        implicit_form = F - C1
        dydx = sp.idiff(implicit_form, y, x)
        verified = sp.simplify(dydx - (-M / N)) == 0

    except Exception:
        verified = False

    return {
        "M": M,
        "N": N,
        "dM_dy": dM_dy,
        "dN_dx": dN_dx,
        "is_exact": is_exact,
        "F": F,
        "solution": solution,
        "verified": verified
    }
