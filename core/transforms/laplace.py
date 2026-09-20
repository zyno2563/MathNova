import sympy as sp

from core.transforms.utils import t, s, build_locals, values_equal


def parse_expression(expression):
    """
    Convert a user-entered expression in t into a
    SymPy expression.
    """

    expression = expression.replace("^", "**")

    return sp.sympify(
        expression,
        locals=build_locals(t=t)
    )


def _round_trip_verified(f_expr, F_expr, tolerance_symbolic=True):
    """
    Verify a Laplace transform pair by taking the
    inverse of F(s) and checking it reproduces f(t).
    """

    try:
        recovered = sp.inverse_laplace_transform(
            F_expr, s, t
        )

        return values_equal(recovered, f_expr)

    except Exception:
        return False


def laplace_transform(function_expression):
    """
    Compute the Laplace transform:

        F(s) = L{f(t)} = int_0^oo f(t) e^(-st) dt
    """

    f_expr = parse_expression(function_expression)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "verified": _round_trip_verified(f_expr, F_expr)
    }


def inverse_laplace_transform(function_expression):
    """
    Compute the Inverse Laplace transform:

        f(t) = L^-1{F(s)}
    """

    F_expr = sp.sympify(
        function_expression.replace("^", "**"),
        locals=build_locals(s=s)
    )

    f_expr = sp.inverse_laplace_transform(
        F_expr, s, t
    )

    try:
        F_check = sp.laplace_transform(
            f_expr, t, s, noconds=True
        )

        verified = values_equal(F_check, F_expr)

    except Exception:
        verified = False

    return {
        "F": F_expr,
        "f": f_expr,
        "verified": verified
    }


def first_shifting_theorem(function_expression, a_value):
    """
    First Shifting Theorem:

        L{e^(at) f(t)} = F(s - a)

    where F(s) = L{f(t)}.
    """

    f_expr = parse_expression(function_expression)
    a = sp.sympify(a_value)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    shifted_f = sp.exp(a * t) * f_expr

    direct_transform = sp.laplace_transform(
        shifted_f, t, s, noconds=True
    )

    theorem_result = F_expr.subs(s, s - a)

    verified = values_equal(
        direct_transform, theorem_result
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "shifted_f": shifted_f,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": verified
    }


def second_shifting_theorem(function_expression, a_value):
    """
    Second Shifting Theorem:

        L{f(t - a) u(t - a)} = e^(-as) F(s)

    where u(t - a) is the unit step (Heaviside) function
    and F(s) = L{f(t)}.
    """

    f_expr = parse_expression(function_expression)
    a = sp.sympify(a_value)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    shifted_f = (
        f_expr.subs(t, t - a)
        * sp.Heaviside(t - a)
    )

    direct_transform = sp.laplace_transform(
        shifted_f, t, s, noconds=True
    )

    theorem_result = sp.exp(-a * s) * F_expr

    verified = values_equal(
        direct_transform, theorem_result
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "shifted_f": shifted_f,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": verified
    }


def derivative_property(function_expression, order=1):
    """
    Laplace transform of derivatives:

        L{f'(t)} = s F(s) - f(0)

        L{f''(t)} = s^2 F(s) - s f(0) - f'(0)

    order must be 1 or 2.
    """

    if order not in (1, 2):
        raise ValueError("order must be 1 or 2.")

    f_expr = parse_expression(function_expression)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    derivative_expr = sp.diff(f_expr, t, order)

    direct_transform = sp.laplace_transform(
        derivative_expr, t, s, noconds=True
    )

    f_at_0 = f_expr.subs(t, 0)

    if order == 1:

        theorem_result = s * F_expr - f_at_0

    else:

        f_prime_at_0 = sp.diff(f_expr, t).subs(t, 0)

        theorem_result = (
            s ** 2 * F_expr
            - s * f_at_0
            - f_prime_at_0
        )

    verified = values_equal(
        direct_transform, theorem_result
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "derivative": derivative_expr,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": verified
    }


def integral_property(function_expression):
    """
    Laplace transform of an integral:

        L{ int_0^t f(tau) dtau } = F(s) / s
    """

    f_expr = parse_expression(function_expression)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    tau = sp.Symbol("tau", positive=True)

    integral_expr = sp.integrate(
        f_expr.subs(t, tau), (tau, 0, t)
    )

    direct_transform = sp.laplace_transform(
        integral_expr, t, s, noconds=True
    )

    theorem_result = F_expr / s

    verified = values_equal(
        direct_transform, theorem_result
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "integral": integral_expr,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": verified
    }


def multiplication_by_t(function_expression, power=1):
    """
    Multiplication by t^n:

        L{t^n f(t)} = (-1)^n F^(n)(s)
    """

    if power < 1:
        raise ValueError("power must be a positive integer.")

    f_expr = parse_expression(function_expression)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    multiplied_f = t ** power * f_expr

    direct_transform = sp.laplace_transform(
        multiplied_f, t, s, noconds=True
    )

    theorem_result = (
        (-1) ** power
        * sp.diff(F_expr, s, power)
    )

    verified = values_equal(
        direct_transform, theorem_result
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "multiplied_f": multiplied_f,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": verified
    }


def division_by_t(function_expression):
    """
    Division by t:

        L{ f(t) / t } = int_s^oo F(sigma) dsigma

    valid when lim_(t -> 0) f(t)/t exists.
    """

    f_expr = parse_expression(function_expression)

    F_expr = sp.laplace_transform(
        f_expr, t, s, noconds=True
    )

    divided_f = f_expr / t

    direct_transform = sp.laplace_transform(
        divided_f, t, s, noconds=True
    )

    sigma = sp.Symbol("sigma", positive=True)

    theorem_result = sp.integrate(
        F_expr.subs(s, sigma), (sigma, s, sp.oo)
    )

    verified = values_equal(
        direct_transform, theorem_result
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "divided_f": divided_f,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": verified
    }
