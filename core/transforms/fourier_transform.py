import sympy as sp

from core.safe_parser import parse_math

from core.transforms.utils import x, w, build_locals, values_equal


def parse_expression(expression):
    """
    Convert a user-entered expression in x into a
    SymPy expression.
    """

    expression = expression.replace("^", "**")

    return parse_math(
        expression,
        locals=build_locals(x=x)
    )


def _extract_closed_form(expr):
    """
    SymPy sometimes wraps an integral's result in a
    Piecewise, branch-conditioned on an assumption it
    could not resolve for a symbol declared only 'real'
    (e.g. Eq(Abs(arg(x)), 0), meaning "x is real and
    nonnegative"). The transform pairs here are only
    ever meaningful on that branch, so take it directly
    rather than surfacing the fallback Integral branch.
    """

    if isinstance(expr, sp.Piecewise):
        return expr.args[0][0]

    return expr


def _forward_full(f_expr):
    """F(w) = 1/sqrt(2 pi) int_(-oo)^(oo) f(x) e^(iwx) dx"""

    result = sp.integrate(
        f_expr * sp.exp(sp.I * w * x),
        (x, -sp.oo, sp.oo)
    ) / sp.sqrt(2 * sp.pi)

    return _extract_closed_form(sp.simplify(result))


def _inverse_full(F_expr):
    """f(x) = 1/sqrt(2 pi) int_(-oo)^(oo) F(w) e^(-iwx) dw"""

    result = sp.integrate(
        F_expr * sp.exp(-sp.I * w * x),
        (w, -sp.oo, sp.oo)
    ) / sp.sqrt(2 * sp.pi)

    return _extract_closed_form(sp.simplify(result))


def _forward_sine(f_expr):
    """Fs(w) = sqrt(2/pi) int_0^(oo) f(x) sin(wx) dx"""

    result = sp.sqrt(sp.Integer(2) / sp.pi) * sp.integrate(
        f_expr * sp.sin(w * x), (x, 0, sp.oo)
    )

    return _extract_closed_form(sp.simplify(result))


def _forward_cosine(f_expr):
    """Fc(w) = sqrt(2/pi) int_0^(oo) f(x) cos(wx) dx"""

    result = sp.sqrt(sp.Integer(2) / sp.pi) * sp.integrate(
        f_expr * sp.cos(w * x), (x, 0, sp.oo)
    )

    return _extract_closed_form(sp.simplify(result))


def _inverse_sine_or_cosine(kernel_expr, trig_func):
    """
    Apply the self-reciprocal sine/cosine transform
    formula to kernel_expr (a function of w), returning
    a function of x. trig_func is sp.sin or sp.cos.
    """

    u = sp.Symbol("u", positive=True)

    result = sp.sqrt(sp.Integer(2) / sp.pi) * sp.integrate(
        kernel_expr.subs(w, u) * trig_func(x * u),
        (u, 0, sp.oo)
    )

    return _extract_closed_form(sp.simplify(result))


# =========================================================
# COMPLEX (INFINITE) FOURIER TRANSFORM
#
# Engineering-mathematics symmetric convention:
#
#     F(w) = 1/sqrt(2 pi) int_(-oo)^(oo) f(x) e^(iwx) dx
#     f(x) = 1/sqrt(2 pi) int_(-oo)^(oo) F(w) e^(-iwx) dw
# =========================================================

def fourier_transform(function_expression):
    """
    Compute the complex Fourier transform F(w) of f(x).
    """

    f_expr = parse_expression(function_expression)
    F_expr = _forward_full(f_expr)

    try:
        recovered = _inverse_full(F_expr)
        verified = values_equal(recovered, f_expr)

    except Exception:
        verified = False

    return {
        "f": f_expr,
        "F": F_expr,
        "verified": verified
    }


def inverse_fourier_transform(function_expression):
    """
    Compute the inverse complex Fourier transform f(x)
    of F(w).
    """

    F_expr = parse_math(
        function_expression.replace("^", "**"),
        locals=build_locals(w=w)
    )

    f_expr = _inverse_full(F_expr)

    try:
        F_check = _forward_full(f_expr)
        verified = values_equal(F_check, F_expr)

    except Exception:
        verified = False

    return {
        "F": F_expr,
        "f": f_expr,
        "verified": verified
    }


# =========================================================
# FOURIER SINE / COSINE TRANSFORMS
#
#     Fs(w) = sqrt(2/pi) int_0^(oo) f(x) sin(wx) dx
#     Fc(w) = sqrt(2/pi) int_0^(oo) f(x) cos(wx) dx
#
# Both are self-reciprocal: applying the same formula a
# second time recovers the original function.
# =========================================================

def fourier_sine_transform(function_expression):
    """
    Compute the Fourier sine transform Fs(w) of f(x),
    x > 0.
    """

    f_expr = parse_expression(function_expression)
    Fs_expr = _forward_sine(f_expr)

    try:
        recovered = _inverse_sine_or_cosine(Fs_expr, sp.sin)
        verified = values_equal(recovered, f_expr)

    except Exception:
        verified = False

    return {
        "f": f_expr,
        "Fs": Fs_expr,
        "verified": verified
    }


def inverse_fourier_sine_transform(function_expression):
    """
    Compute the inverse Fourier sine transform.
    Identical formula to the forward transform, since
    the sine transform is self-reciprocal.
    """

    Fs_expr = parse_math(
        function_expression.replace("^", "**"),
        locals=build_locals(w=w)
    )

    f_expr = _inverse_sine_or_cosine(Fs_expr, sp.sin)

    try:
        Fs_check = _forward_sine(f_expr)
        verified = values_equal(Fs_check, Fs_expr)

    except Exception:
        verified = False

    return {
        "Fs": Fs_expr,
        "f": f_expr,
        "verified": verified
    }


def fourier_cosine_transform(function_expression):
    """
    Compute the Fourier cosine transform Fc(w) of f(x),
    x > 0.
    """

    f_expr = parse_expression(function_expression)
    Fc_expr = _forward_cosine(f_expr)

    try:
        recovered = _inverse_sine_or_cosine(Fc_expr, sp.cos)
        verified = values_equal(recovered, f_expr)

    except Exception:
        verified = False

    return {
        "f": f_expr,
        "Fc": Fc_expr,
        "verified": verified
    }


def inverse_fourier_cosine_transform(function_expression):
    """
    Compute the inverse Fourier cosine transform.
    Identical formula to the forward transform, since
    the cosine transform is self-reciprocal.
    """

    Fc_expr = parse_math(
        function_expression.replace("^", "**"),
        locals=build_locals(w=w)
    )

    f_expr = _inverse_sine_or_cosine(Fc_expr, sp.cos)

    try:
        Fc_check = _forward_cosine(f_expr)
        verified = values_equal(Fc_check, Fc_expr)

    except Exception:
        verified = False

    return {
        "Fc": Fc_expr,
        "f": f_expr,
        "verified": verified
    }


# =========================================================
# PROPERTIES
# =========================================================

def shifting_property(function_expression, a_value):
    """
    Shifting property:

        F{f(x - a)} = e^(iwa) F(w)
    """

    f_expr = parse_expression(function_expression)
    a = parse_math(a_value)

    F_expr = _forward_full(f_expr)

    shifted_f = f_expr.subs(x, x - a)
    direct_transform = _forward_full(shifted_f)

    theorem_result = sp.exp(sp.I * w * a) * F_expr

    return {
        "f": f_expr,
        "F": F_expr,
        "shifted_f": shifted_f,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": values_equal(
            direct_transform, theorem_result
        )
    }


def scaling_property(function_expression, a_value):
    """
    Change of scale property:

        F{f(ax)} = 1/|a| F(w/a)
    """

    f_expr = parse_expression(function_expression)
    a = parse_math(a_value)

    if a == 0:
        raise ValueError("a must be non-zero.")

    F_expr = _forward_full(f_expr)

    scaled_f = f_expr.subs(x, a * x)
    direct_transform = _forward_full(scaled_f)

    theorem_result = (
        F_expr.subs(w, w / a) / sp.Abs(a)
    )

    return {
        "f": f_expr,
        "F": F_expr,
        "scaled_f": scaled_f,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": values_equal(
            direct_transform, theorem_result
        )
    }
