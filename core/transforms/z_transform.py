import sympy as sp

from core.safe_parser import parse_math

from core.transforms.utils import n, z, build_locals, values_equal


def parse_expression(expression):
    """
    Convert a user-entered expression in n into a
    SymPy expression. Any other free symbol (e.g. a
    parameter like theta or a) is treated as real, so
    later complex-number bookkeeping doesn't decompose
    it into re()/im() pieces.
    """

    expression = expression.replace("^", "**")

    parsed = parse_math(
        expression,
        locals=build_locals(n=n)
    )

    return _realize_free_symbols(parsed, exclude=(n,))


def _realize_free_symbols(expr, exclude=()):
    """
    Substitute a real-assumed Symbol of the same name for
    every free symbol not in `exclude` (typically the
    transform's own variable, which must stay a general
    complex symbol). Avoids re()/im() decomposition of
    incidental parameters like theta or a.
    """

    substitutions = {
        symbol: sp.Symbol(symbol.name, real=True)
        for symbol in expr.free_symbols
        if symbol not in exclude and not symbol.is_real
    }

    return expr.subs(substitutions)


def _normalize_exponentials(expr):
    """
    Rewrite any Pow(base, exponent) where the exponent
    depends on n (e.g. a**(n - 2)) into exp(exponent *
    log(base)) form, so every n-dependent factor can be
    combined into a single exponential term below.
    """

    return expr.replace(
        lambda e: (
            e.is_Pow
            and e.exp.has(n)
            and not e.base.has(n)
            and e.base.func != sp.exp
        ),
        lambda e: sp.exp(e.exp * sp.log(e.base))
    )


def _match_power_and_ratio(dependent):
    """
    Decompose an n-dependent factor into (power, ratio)
    such that dependent == n**power * ratio**n.
    """

    dependent = sp.powsimp(dependent, combine="exp", force=True)

    if dependent == 1:
        return 0, sp.Integer(1)

    factors = dependent.as_ordered_factors()

    exponent_sum = 0
    found_exp = False
    poly_part = sp.Integer(1)

    for factor in factors:

        if factor.func == sp.exp:
            exponent_sum += factor.args[0]
            found_exp = True

        else:
            poly_part *= factor

    if found_exp:

        c = exponent_sum.coeff(n)

        if sp.simplify(exponent_sum - c * n) != 0:
            raise ValueError(
                f"Unsupported exponential term: {dependent}"
            )

        ratio = sp.exp(c)

    else:
        ratio = sp.Integer(1)

    if poly_part == 1:
        power = 0

    else:
        k_wild = sp.Wild("k", exclude=[n])
        match = poly_part.match(n ** k_wild)

        if match is None:
            raise ValueError(
                f"Unsupported polynomial factor: {poly_part}"
            )

        power = match[k_wild]

    return power, ratio


def z_transform(sequence_expression):
    """
    Compute the Z-transform:

        X(z) = sum_(n=0)^(oo) x(n) z^(-n)

    Works for any sequence expressible as a sum of terms
    of the form C * n^k * r^n (covers unit step, ramp,
    a^n, n a^n, n^2 a^n, cos(n theta), sin(n theta), and
    products/combinations of these), by applying the
    elementary geometric series sum

        sum_(n=0)^(oo) r^n z^(-n) = z / (z - r)

    to each term and, for the n^k factor, the standard
    "multiply by n" operator relation:

        Z{n x(n)} = -z dX/dz
    """

    x_n = parse_expression(sequence_expression)
    X_expr = z_transform_expr(x_n)

    try:
        verified = _verify_by_series(x_n, X_expr)

    except Exception:
        verified = False

    return {
        "x_n": x_n,
        "X": X_expr,
        "verified": verified
    }


def _verify_by_series(x_n_expr, X_expr, num_terms=6):
    """
    Independently verify X(z) by Laurent-expanding it in
    w = 1/z around w = 0: the coefficient of w^k must
    equal x(k) for k = 0 .. num_terms-1.
    """

    w_dummy = sp.Symbol("w_dummy__")

    series_expr = X_expr.subs(z, 1 / w_dummy)
    series = sp.series(
        series_expr, w_dummy, 0, num_terms
    ).removeO()

    series_poly = sp.Poly(series, w_dummy)

    for k in range(num_terms):

        coeff = series_poly.coeff_monomial(w_dummy ** k)
        expected = x_n_expr.subs(n, k)

        if not values_equal(coeff, expected):
            return False

    return True


def inverse_z_transform(function_expression):
    """
    Compute the inverse Z-transform x(n) of a rational
    X(z), via partial fraction decomposition of X(z)/z:

        X(z)/z = sum_i A_i / (a_i z + b_i)^(m_i)

    Each term maps back to a sequence using:

        Z^(-1){ z / (z - p)^m } = C(n, m-1) p^(n-m+1)

    Handles simple and repeated poles, real or complex
    conjugate pairs.
    """

    X_expr = parse_math(
        function_expression.replace("^", "**"),
        locals=build_locals(z=z)
    )
    X_expr = _realize_free_symbols(X_expr, exclude=(z,))

    Y = sp.apart(X_expr / z, z, extension=[sp.I])

    a_wild = sp.Wild("a", exclude=[z])
    b_wild = sp.Wild("b", exclude=[z])
    m_wild = sp.Wild("m")

    x_n = 0

    for term in sp.Add.make_args(Y):

        coeff, rest = term.as_independent(z)

        match = rest.match(1 / (a_wild * z + b_wild) ** m_wild)

        if match is None or not match[m_wild].is_number:
            raise ValueError(
                f"Unsupported partial fraction term: {term}"
            )

        a_val = match[a_wild]
        b_val = match[b_wild]
        m_val = int(match[m_wild])

        p_val = -b_val / a_val
        term_coeff = coeff / a_val ** m_val

        x_n += (
            term_coeff
            * sp.binomial(n, m_val - 1)
            * p_val ** (n - m_val + 1)
        )

    x_n = sp.expand_complex(sp.simplify(x_n))
    x_n = sp.simplify(x_n)

    try:
        X_check = z_transform_expr(x_n)
        verified = values_equal(
            sp.together(X_check), sp.together(X_expr)
        )

    except Exception:
        verified = False

    return {
        "X": X_expr,
        "x_n": x_n,
        "verified": verified
    }


def z_transform_expr(x_n_expr):
    """
    Internal helper: same algorithm as z_transform(),
    operating directly on an already-parsed sequence
    expression instead of a text string.
    """

    prepared = sp.expand_func(x_n_expr)
    prepared = _normalize_exponentials(prepared)
    rewritten = sp.expand(prepared.rewrite(sp.exp))

    z_dummy = sp.Symbol("z_dummy__", real=True)

    total = 0

    for term in sp.Add.make_args(rewritten):

        coeff, dependent = term.as_independent(n)
        power, ratio = _match_power_and_ratio(dependent)

        term_transform = z_dummy / (z_dummy - ratio)

        for _ in range(int(power)):
            term_transform = sp.together(
                -z_dummy * sp.diff(term_transform, z_dummy)
            )

        total += coeff * term_transform

    if total.has(sp.I):
        total = sp.expand_complex(total)

    total = sp.simplify(total)

    return total.subs(z_dummy, z)


# =========================================================
# PROPERTIES
# =========================================================

def linearity_property(
    sequence_1_expression,
    sequence_2_expression,
    a_value,
    b_value
):
    """
    Linearity property:

        Z{a x1(n) + b x2(n)} = a X1(z) + b X2(z)
    """

    x1 = parse_expression(sequence_1_expression)
    x2 = parse_expression(sequence_2_expression)

    a = parse_math(a_value)
    b = parse_math(b_value)

    X1 = z_transform_expr(x1)
    X2 = z_transform_expr(x2)

    combined_sequence = a * x1 + b * x2

    direct_transform = z_transform_expr(combined_sequence)
    theorem_result = sp.simplify(a * X1 + b * X2)

    return {
        "x1": x1,
        "x2": x2,
        "X1": X1,
        "X2": X2,
        "combined_sequence": combined_sequence,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": values_equal(
            direct_transform, theorem_result
        )
    }


def scaling_theorem(sequence_expression, a_value):
    """
    Scaling (multiplication) theorem:

        Z{a^n x(n)} = X(z / a)
    """

    x_n = parse_expression(sequence_expression)
    a = parse_math(a_value)

    if a == 0:
        raise ValueError("a must be non-zero.")

    X_expr = z_transform_expr(x_n)

    scaled_sequence = a ** n * x_n
    direct_transform = z_transform_expr(scaled_sequence)

    theorem_result = sp.simplify(X_expr.subs(z, z / a))

    return {
        "x_n": x_n,
        "X": X_expr,
        "scaled_sequence": scaled_sequence,
        "direct_transform": direct_transform,
        "theorem_result": theorem_result,
        "verified": values_equal(
            direct_transform, theorem_result
        )
    }


def time_shifting_theorem(sequence_expression, k_value):
    """
    Time-shifting (delay) theorem, for a causal sequence
    x(n) (x(n) = 0 for n < 0) and integer k >= 0:

        Z{x(n - k)} = z^(-k) X(z)
    """

    k = int(k_value)

    if k < 0:
        raise ValueError("k must be a non-negative integer.")

    x_n = parse_expression(sequence_expression)
    X_expr = z_transform_expr(x_n)

    theorem_result = sp.simplify(z ** (-k) * X_expr)

    try:
        direct_sum = sp.summation(
            x_n.subs(n, n - k) * z ** (-n), (n, k, sp.oo)
        )

        if isinstance(direct_sum, sp.Piecewise):
            direct_sum = direct_sum.args[0][0]

        verified = values_equal(direct_sum, theorem_result)

    except Exception:
        verified = None

    return {
        "x_n": x_n,
        "X": X_expr,
        "k": k,
        "theorem_result": theorem_result,
        "verified": verified
    }


def initial_value_theorem(function_expression):
    """
    Initial value theorem:

        x(0) = lim_(z -> oo) X(z)
    """

    X_expr = parse_math(
        function_expression.replace("^", "**"),
        locals=build_locals(z=z)
    )

    initial_value = sp.limit(X_expr, z, sp.oo)

    try:
        sequence = inverse_z_transform(str(X_expr))["x_n"]
        direct_value = sp.simplify(sequence.subs(n, 0))

        verified = values_equal(initial_value, direct_value)

    except Exception:
        verified = False

    return {
        "X": X_expr,
        "initial_value": initial_value,
        "verified": verified
    }


def final_value_theorem(function_expression):
    """
    Final value theorem (valid when (z-1)X(z) has all
    poles inside the unit circle):

        lim_(n -> oo) x(n) = lim_(z -> 1) (z - 1) X(z)
    """

    X_expr = parse_math(
        function_expression.replace("^", "**"),
        locals=build_locals(z=z)
    )

    final_value = sp.limit(
        (z - 1) * X_expr, z, 1
    )

    try:
        sequence = inverse_z_transform(str(X_expr))["x_n"]
        direct_value = sp.limit(sequence, n, sp.oo)

        verified = values_equal(final_value, direct_value)

    except Exception:
        verified = False

    return {
        "X": X_expr,
        "final_value": final_value,
        "verified": verified
    }
