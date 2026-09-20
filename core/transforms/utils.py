import sympy as sp


# Laplace transform variables
t = sp.Symbol("t", positive=True)
s = sp.Symbol("s")

# Fourier transform variables (x: space/time, w: frequency)
# w is taken positive so SymPy's integrals resolve to a
# clean closed form instead of a branch-conditioned
# Piecewise; the resulting formulas remain valid for all
# real w, matching standard engineering-math tables.
x = sp.Symbol("x", real=True)
w = sp.Symbol("w", positive=True)

# Z-transform variables (n: discrete time, z: complex frequency)
n = sp.Symbol("n", integer=True, nonnegative=True)
z = sp.Symbol("z")


COMMON_FUNCTIONS = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "sqrt": sp.sqrt,
    "abs": sp.Abs,
    "pi": sp.pi,
    "e": sp.E,
    "E": sp.E,
    "Heaviside": sp.Heaviside,
    "DiracDelta": sp.DiracDelta
}


def build_locals(**symbol_bindings):
    """
    Build the locals dict passed to sp.sympify: the
    common function names, plus the caller's chosen
    free-variable bindings (e.g. t=t for Laplace).
    """

    locals_dict = dict(COMMON_FUNCTIONS)
    locals_dict.update(symbol_bindings)

    return locals_dict


def values_equal(expr1, expr2):
    """
    Check whether two SymPy expressions are equal.

    Tries exact symbolic simplification first. Falls
    back to numeric evaluation at sample points, since
    sp.simplify() sometimes cannot resolve identities
    (e.g. atan(1/s) + atan(s) == pi/2 for s > 0) without
    sign assumptions that get lost during derivation.
    """

    difference = sp.simplify(expr1 - expr2)

    if difference == 0:
        return True

    free_symbols = list(difference.free_symbols)

    if not free_symbols:
        try:
            return abs(complex(difference)) < 1e-9
        except Exception:
            return False

    try:
        substitutions = {
            symbol: 1.3 + 0.7 * index
            for index, symbol in enumerate(free_symbols)
        }

        numeric_difference = complex(
            difference.evalf(subs=substitutions)
        )

        return abs(numeric_difference) < 1e-6

    except Exception:
        return False
