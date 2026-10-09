import sympy as sp

from core.safe_parser import parse_math


x = sp.symbols("x", real=True)
m = sp.symbols("m")

def parse_expression(expression):
    """
    Convert a user-entered expression into a SymPy expression.
    """

    expression = expression.replace("^", "**")

    allowed_functions = {
    "x": x,
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


def complementary_function(coefficients):
    """
    Calculate the Complementary Function (CF)
    for a linear ODE with constant coefficients.

    coefficients:
        [a_n, a_(n-1), ..., a_1, a_0]

    Example:

        D^2 - 3D + 2

        coefficients = [1, -3, 2]
    """

    order = len(coefficients) - 1

    auxiliary_equation = sum(
        coefficients[i] * m ** (order - i)
        for i in range(len(coefficients))
    )

    roots = sp.roots(
        auxiliary_equation,
        m
    )

    cf = build_cf(
        roots,
        order
    )

    return (
        auxiliary_equation,
        roots,
        cf
    )


def build_cf(roots, order):
    """
    Build the Complementary Function from
    real and complex characteristic roots.

    Handles:

    1. Distinct real roots
    2. Repeated real roots
    3. Complex conjugate roots
    4. Repeated complex roots
    """

    constants = []
    constant_number = 1

    terms = []

    processed = set()

    for root, multiplicity in roots.items():

        if root in processed:
            continue

        real_part = sp.re(root)
        imaginary_part = sp.im(root)

        # -------------------------------------------------
        # REAL ROOT
        # -------------------------------------------------

        if imaginary_part == 0:

            real_root = sp.simplify(real_part)

            for repetition in range(multiplicity):

                C = sp.Symbol(
                    f"C{constant_number}"
                )

                constant_number += 1

                term = (
                    C
                    * x ** repetition
                    * sp.exp(real_root * x)
                )

                terms.append(term)

            processed.add(root)

        # -------------------------------------------------
        # COMPLEX ROOT
        # -------------------------------------------------

        else:

            imaginary_part = sp.simplify(
                abs(imaginary_part)
            )

            conjugate_root = sp.conjugate(root)

            # Only process one root of the
            # conjugate pair.
            if conjugate_root in roots:

                for repetition in range(multiplicity):

                    C1 = sp.Symbol(
                        f"C{constant_number}"
                    )

                    C2 = sp.Symbol(
                        f"C{constant_number + 1}"
                    )

                    constant_number += 2

                    term = (
                        x ** repetition
                        * sp.exp(real_part * x)
                        * (
                            C1 * sp.cos(
                                imaginary_part * x
                            )
                            +
                            C2 * sp.sin(
                                imaginary_part * x
                            )
                        )
                    )

                    terms.append(term)

                processed.add(root)
                processed.add(conjugate_root)

            else:

                raise ValueError(
                    "Complex root does not have "
                    "a conjugate pair."
                )

    return sp.Add(*terms)


def particular_integral(
    coefficients,
    forcing_expression
):
    """
    Calculate the complete differential equation
    solution using SymPy.

    PI extraction will be added separately.
    """

    y = sp.Function("y")

    order = len(coefficients) - 1

    derivative_terms = []

    for i, coefficient in enumerate(coefficients):

        derivative_order = (
            order - i
        )

        if derivative_order == 0:

            term = (
                coefficient * y(x)
            )

        else:

            term = (
                coefficient
                * sp.diff(
                    y(x),
                    x,
                    derivative_order
                )
            )

        derivative_terms.append(term)

    ode = sp.Eq(
        sum(derivative_terms),
        forcing_expression
    )

    return sp.dsolve(
        ode
    )

def particular_integral_exponential(
    coefficients,
    a
):
    """
    Calculate PI for:

        F(D)y = e^(ax)

    Non-resonant case:

        PI = e^(ax) / F(a)

    Resonant case:

        If a is a root of F(D) with multiplicity r,

        PI = r! * x^r * e^(ax) / F^(r)(a)
    """

    order = len(coefficients) - 1

    F = sum(
        coefficients[i] * m ** (order - i)
        for i in range(len(coefficients))
    )

    F_at_a = sp.simplify(
        F.subs(m, a)
    )

    # Normal case
    if F_at_a != 0:

        pi = (
            sp.exp(a * x)
            / F_at_a
        )

        return {
            "operator": F,
            "F_a": F_at_a,
            "resonance": False,
            "multiplicity": 0,
            "pi": sp.simplify(pi)
        }

    # Resonance
    roots = sp.roots(F, m)

    multiplicity = roots.get(
        parse_math(a),
        0
    )

    if multiplicity == 0:

        raise ValueError(
            "Unable to determine root multiplicity."
        )

    derivative = sp.diff(
        F,
        m,
        multiplicity
    )

    derivative_at_a = sp.simplify(
        derivative.subs(m, a)
    )

    if derivative_at_a == 0:

        raise ValueError(
            "Unable to calculate resonant PI."
        )

    pi = (
        sp.factorial(multiplicity)
        * x ** multiplicity
        * sp.exp(a * x)
        / derivative_at_a
    )

    return {
        "operator": F,
        "F_a": F_at_a,
        "resonance": True,
        "multiplicity": multiplicity,
        "derivative_order": multiplicity,
        "derivative_at_a": derivative_at_a,
        "pi": sp.simplify(pi)
    }

def particular_integral_trigonometric(
    coefficients,
    a,
    function_type
):
    """
    Calculate the Particular Integral for:

        F(D)y = sin(ax)

    or:

        F(D)y = cos(ax)

    Handles normal and resonant cases.
    """

    order = len(coefficients) - 1

    F = sum(
        coefficients[i] * m ** (order - i)
        for i in range(len(coefficients))
    )

    # Complex characteristic value
    lam = sp.I * a

    F_at_lam = sp.simplify(
        F.subs(m, lam)
    )

    # -------------------------------------------------
    # NORMAL CASE
    # -------------------------------------------------

    if F_at_lam != 0:

        complex_pi = (
            sp.exp(lam * x)
            / F_at_lam
        )

        if function_type.lower() == "sin":

            pi = sp.im(
                sp.expand_complex(complex_pi)
            )

        elif function_type.lower() == "cos":

            pi = sp.re(
                sp.expand_complex(complex_pi)
            )

        else:

            raise ValueError(
                "function_type must be 'sin' or 'cos'."
            )

        return {
            "operator": F,
            "F_ia": F_at_lam,
            "resonance": False,
            "multiplicity": 0,
            "pi": sp.simplify(pi)
        }

    # -------------------------------------------------
    # RESONANCE
    # -------------------------------------------------

    roots = sp.roots(
        F,
        m
    )

    multiplicity = roots.get(
        lam,
        0
    )

    if multiplicity == 0:

        raise ValueError(
            "Unable to determine the resonant root "
            "multiplicity."
        )

    derivative = sp.diff(
        F,
        m,
        multiplicity
    )

    derivative_at_lam = sp.simplify(
        derivative.subs(m, lam)
    )

    if derivative_at_lam == 0:

        raise ValueError(
            "Unable to calculate resonant PI."
        )

    complex_pi = (
        sp.factorial(multiplicity)
        * x ** multiplicity
        * sp.exp(lam * x)
        / derivative_at_lam
    )

    if function_type.lower() == "sin":

      pi = sp.simplify(
    sp.im(
        sp.expand_complex(complex_pi)
    )
)

    elif function_type.lower() == "cos":

     pi = sp.simplify(
    sp.re(
        sp.expand_complex(complex_pi)
    )
)

    else:

        raise ValueError(
            "function_type must be 'sin' or 'cos'."
        )

    return {
        "operator": F,
        "F_ia": F_at_lam,
        "resonance": True,
        "multiplicity": multiplicity,
        "derivative_order": multiplicity,
        "derivative_at_ia": derivative_at_lam,
        "pi": sp.simplify(pi)
    }

def particular_integral_polynomial(
    coefficients,
    forcing_expression
):
    """
    Calculate PI for a polynomial RHS X(x)
    using operator/binomial expansion.

    Example:

        (D^2 - 3D + 2)y = x^2

    coefficients = [1, -3, 2]
    forcing_expression = "x^2"
    """

    X = parse_expression(
        forcing_expression
    )

    # Make sure RHS is a polynomial in x
    if not X.is_polynomial(x):
        raise ValueError(
            "Forcing expression must be a polynomial in x."
        )

    polynomial = sp.Poly(
        X,
        x
    )

    degree = polynomial.degree()

    # -------------------------------------------------
    # Build F(D)
    # -------------------------------------------------

    order = len(coefficients) - 1

    F = sum(
        coefficients[i] * m ** (order - i)
        for i in range(len(coefficients))
    )

    # -------------------------------------------------
    # Factor out powers of D if F(0) = 0
    # -------------------------------------------------

    zero_multiplicity = 0

    while sp.simplify(
        F.subs(m, 0)
    ) == 0:

        zero_multiplicity += 1
        F = sp.cancel(F / m)

    # -------------------------------------------------
    # F(D) now has a non-zero constant term
    # -------------------------------------------------

    F0 = sp.simplify(
        F.subs(m, 0)
    )

    # Coefficients of F(D)
    F_poly = sp.Poly(
        F,
        m
    )

    operator_coefficients = {
        power: sp.simplify(
            F_poly.coeff_monomial(m ** power)
        )
        for power in range(
            degree + 1
        )
    }

    # -------------------------------------------------
    # Find coefficients of 1/F(D)
    #
    # q(D) = q0 + q1 D + q2 D^2 + ...
    #
    # F(D)q(D) = 1
    # -------------------------------------------------

    inverse_coefficients = []

    q0 = sp.simplify(
        1 / F0
    )

    inverse_coefficients.append(q0)

    for n in range(1, degree + 1):

        total = 0

        for k in range(1, n + 1):

            F_k = operator_coefficients.get(
                k,
                0
            )

            q_previous = inverse_coefficients[
                n - k
            ]

            total += (
                F_k
                * q_previous
            )

        q_n = sp.simplify(
            -total / F0
        )

        inverse_coefficients.append(
            q_n
        )

    # -------------------------------------------------
    # Apply inverse operator to X
    # -------------------------------------------------

    result = 0

    derivative_steps = []

    for n, q_n in enumerate(
        inverse_coefficients
    ):

        if q_n == 0:
            continue

        derivative = sp.diff(
            X,
            x,
            n
        )

        if derivative == 0:
            break

        term = sp.simplify(
            q_n * derivative
        )

        result += term

        derivative_steps.append(
            {
                "order": n,
                "coefficient": q_n,
                "derivative": derivative,
                "term": term
            }
        )

    result = sp.simplify(
        result
    )

    # -------------------------------------------------
    # If D^r was factored out,
    #
    # 1 / D^r  -> integrate r times
    # -------------------------------------------------

    for _ in range(
        zero_multiplicity
    ):

        result = sp.integrate(
            result,
            x
        )

    return {
        "original_operator": sum(
            coefficients[i]
            * m ** (order - i)
            for i in range(len(coefficients))
        ),
        "reduced_operator": F,
        "forcing": X,
        "degree": degree,
        "zero_multiplicity": zero_multiplicity,
        "inverse_coefficients": inverse_coefficients,
        "derivative_steps": derivative_steps,
        "pi": sp.simplify(result)
    }

def particular_integral_exponential_function(
    coefficients,
    a,
    function_expression
):
    """
    Calculate PI for:

        F(D)y = e^(ax) V(x)

    using the shift theorem:

        PI = e^(ax) [1 / F(D+a)] V(x)

    Currently V(x) must be a polynomial.
    """

    V = parse_expression(
        function_expression
    )

    if not V.is_polynomial(x):
        raise ValueError(
            "V(x) must be a polynomial."
        )

    degree = sp.Poly(
        V,
        x
    ).degree()

    order = len(coefficients) - 1

    # Original operator F(D)
    F = sum(
        coefficients[i] * m ** (order - i)
        for i in range(len(coefficients))
    )

    # Shifted operator F(D + a)
    shifted_operator = sp.expand(
        F.subs(
            m,
            m + a
        )
    )

    # Convert shifted operator into
    # polynomial in D
    shifted_poly = sp.Poly(
        shifted_operator,
        m
    )

    F_shift_0 = sp.simplify(
        shifted_poly.coeff_monomial(
            1
        )
    )

    if F_shift_0 == 0:
        raise ValueError(
            "Shifted operator has zero constant term. "
            "A resonant exponential-function case "
            "needs special handling."
        )

    # -------------------------------------------------
    # Build inverse operator
    # -------------------------------------------------

    inverse_coefficients = []

    q0 = sp.simplify(
        1 / F_shift_0
    )

    inverse_coefficients.append(
        q0
    )

    for n in range(
        1,
        degree + 1
    ):

        total = 0

        for k in range(
            1,
            n + 1
        ):

            F_k = shifted_poly.coeff_monomial(
                m ** k
            )

            q_previous = inverse_coefficients[
                n - k
            ]

            total += (
                F_k
                * q_previous
            )

        q_n = sp.simplify(
            -total / F_shift_0
        )

        inverse_coefficients.append(
            q_n
        )

    # -------------------------------------------------
    # Apply inverse shifted operator to V(x)
    # -------------------------------------------------

    result = 0

    derivative_steps = []

    for n, q_n in enumerate(
        inverse_coefficients
    ):

        derivative = sp.diff(
            V,
            x,
            n
        )

        if derivative == 0:
            break

        term = sp.simplify(
            q_n * derivative
        )

        result += term

        derivative_steps.append(
            {
                "order": n,
                "coefficient": q_n,
                "derivative": derivative,
                "term": term
            }
        )

    polynomial_pi = sp.simplify(
        result
    )

    pi = sp.simplify(
        sp.exp(a * x)
        * polynomial_pi
    )

    return {
        "operator": F,
        "shifted_operator": shifted_operator,
        "forcing_function": V,
        "shift": a,
        "degree": degree,
        "inverse_coefficients": inverse_coefficients,
        "derivative_steps": derivative_steps,
        "polynomial_pi": polynomial_pi,
        "pi": pi
    }

def apply_operator(coefficients, solution):
    """
    Apply the differential operator F(D) to a solution.

    coefficients = [a_n, a_(n-1), ..., a_1, a_0]
    """

    order = len(coefficients) - 1

    result = 0

    for i, coefficient in enumerate(coefficients):

        derivative_order = order - i

        if derivative_order == 0:
            term = coefficient * solution

        else:
            term = (
                coefficient
                * sp.diff(
                    solution,
                    x,
                    derivative_order
                )
            )

        result += term

    return sp.simplify(result)


def verify_ode_solution(
    coefficients,
    solution,
    forcing_expression
):
    """
    Verify:

        F(D)y = RHS
    """

    if isinstance(forcing_expression, str):
        forcing = parse_expression(
            forcing_expression
        )
    else:
        forcing = forcing_expression

    lhs = apply_operator(
        coefficients,
        solution
    )

    difference = sp.simplify(
        sp.expand(lhs - forcing)
    )

    return {
        "lhs": sp.simplify(lhs),
        "rhs": sp.simplify(forcing),
        "difference": difference,
        "verified": difference == 0
    }


def build_complete_solution(
    coefficients,
    cf,
    pi,
    forcing_expression
):
    """
    Build:

        y = CF + PI

    and verify CF, PI and the complete solution.
    """

    complete_solution = sp.simplify(
        cf + pi
    )

    # -----------------------------
    # CF verification
    # -----------------------------

    cf_lhs = apply_operator(
        coefficients,
        cf
    )

    cf_difference = sp.simplify(
        cf_lhs
    )

    cf_verification = {
        "lhs": cf_lhs,
        "difference": cf_difference,
        "verified": cf_difference == 0
    }

    # -----------------------------
    # PI verification
    # -----------------------------

    pi_verification = verify_ode_solution(
        coefficients,
        pi,
        forcing_expression
    )

    # -----------------------------
    # Complete solution verification
    # -----------------------------

    complete_verification = verify_ode_solution(
        coefficients,
        complete_solution,
        forcing_expression
    )

    return {
        "cf": sp.simplify(cf),
        "pi": sp.simplify(pi),
        "complete_solution": complete_solution,

        "cf_verification": cf_verification,

        "pi_verification": pi_verification,

        "complete_verification": complete_verification
    }