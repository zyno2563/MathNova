import sympy as sp

from core.safe_parser import parse_math


x, y, z = sp.symbols("x y z", real=True)
p, q = sp.symbols("p q")
a, b = sp.symbols("a b")

C1, C2 = sp.symbols("C1 C2")
K1 = sp.Symbol("K1")


def parse_expression(expression):
    """
    Convert a user-entered expression (in x, y, z, p, q)
    into a SymPy expression.
    """

    expression = expression.replace("^", "**")

    allowed_functions = {
        "x": x,
        "y": y,
        "z": z,
        "p": p,
        "q": q,
        "a": a,
        "b": b,
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


def _isolate_constant(rhs_expression, variable, constant):
    """
    Solve rhs_expression = variable for `constant`.

    Falls back to squaring both sides first, since
    dsolve() frequently returns relations wrapped in a
    square root (e.g. y = sqrt(C1 + x**2)) that `solve`
    cannot invert directly for the constant.
    """

    solutions = sp.solve(
        sp.Eq(rhs_expression, variable),
        constant
    )

    if solutions:
        return sp.simplify(solutions[0])

    solutions = sp.solve(
        sp.Eq(rhs_expression ** 2, variable ** 2),
        constant
    )

    if solutions:
        return sp.simplify(solutions[0])

    raise ValueError(
        f"Could not isolate the constant {constant} "
        "from the characteristic solution."
    )


# =========================================================
# FORMATION OF PDE
# =========================================================

def eliminate_arbitrary_constants(z_expression, constant_names):
    """
    Form a first-order PDE by eliminating one or two
    arbitrary constants from:

        z = f(x, y; constants)

    A first-order PDE only carries p = dz/dx and
    q = dz/dy, so at most two arbitrary constants can be
    eliminated this way.
    """

    z_expr = parse_expression(z_expression)

    constants = [
        sp.Symbol(name) if isinstance(name, str) else name
        for name in constant_names
    ]

    if len(constants) not in (1, 2):
        raise ValueError(
            "Provide exactly one or two arbitrary constants."
        )

    p_expr = sp.diff(z_expr, x)
    q_expr = sp.diff(z_expr, y)

    equations = {
        "p": sp.Eq(p, p_expr),
        "q": sp.Eq(q, q_expr),
        "z": sp.Eq(z, z_expr)
    }

    if len(constants) == 2:

        pair_order = [
            ("p", "q"),
            ("p", "z"),
            ("q", "z")
        ]

        for key_1, key_2 in pair_order:

            solution = sp.solve(
                [equations[key_1], equations[key_2]],
                constants,
                dict=True
            )

            if not solution:
                continue

            solved = solution[0]

            if len(solved) != len(constants):
                continue

            leftover_key = (
                {"p", "q", "z"} - {key_1, key_2}
            ).pop()

            leftover_equation = equations[leftover_key]

            pde_expression = sp.simplify(
                leftover_equation.lhs
                - leftover_equation.rhs.subs(solved)
            )

            return {
                "z": z_expr,
                "p": p_expr,
                "q": q_expr,
                "constants_solved": solved,
                "pde": sp.Eq(pde_expression, 0),
                "verified": _verify_constants_elimination(
                    pde_expression,
                    z_expr,
                    p_expr,
                    q_expr
                )
            }

        raise ValueError(
            "Could not eliminate the two arbitrary "
            "constants using p and q."
        )

    # -----------------------------------------------------
    # ONE CONSTANT
    # -----------------------------------------------------

    constant = constants[0]

    for key in ["p", "q"]:

        solution = sp.solve(
            equations[key],
            constant
        )

        if not solution:
            continue

        constant_value = solution[0]

        pde_expression = sp.simplify(
            z_expr.subs(constant, constant_value) - z
        )

        return {
            "z": z_expr,
            "p": p_expr,
            "q": q_expr,
            "constants_solved": {constant: constant_value},
            "pde": sp.Eq(pde_expression, 0),
            "verified": _verify_constants_elimination(
                pde_expression,
                z_expr,
                p_expr,
                q_expr
            )
        }

    raise ValueError(
        "Could not eliminate the arbitrary constant "
        "using p or q."
    )


def _verify_constants_elimination(
    pde_expression,
    z_expr,
    p_expr,
    q_expr
):
    """
    Independently verify that substituting the original
    z, p and q (still in terms of the un-eliminated
    constants) back into the derived PDE collapses it
    identically to zero.
    """

    try:
        check = sp.simplify(
            pde_expression.subs({
                z: z_expr,
                p: p_expr,
                q: q_expr
            })
        )

        return check == 0

    except Exception:
        return False


# =========================================================
# LAGRANGE'S LINEAR PDE:  Pp + Qq = R
# =========================================================

def lagrange_linear_pde(P_expression, Q_expression, R_expression):
    """
    Solve Lagrange's linear PDE:

        P(x, y, z) p + Q(x, y, z) q = R(x, y, z)

    using the subsidiary (characteristic) equations:

        dx/P = dy/Q = dz/R

    Two independent solutions (invariants) u(x, y, z) = C1
    and v(x, y, z) = C2 are found by solving the
    characteristic curves sequentially:

        1. dy/dx = Q/P  ->  u(x, y) = C1
        2. dz/dx = R/P  (with y eliminated via step 1)
           -> v(x, y, z) = C2

    The general solution is F(u, v) = 0 for an arbitrary
    function F.

    Note: this sequential approach covers the common
    textbook cases where dy/dx = Q/P does not itself
    depend on z. Equations that require the method of
    multipliers to decouple are not handled automatically.
    """

    P = parse_expression(P_expression)
    Q = parse_expression(Q_expression)
    R = parse_expression(R_expression)

    if sp.simplify(P) == 0:
        raise ValueError(
            "P must be non-zero for this solving strategy "
            "(dy/dx = Q/P is undefined)."
        )

    # -------------------------------------------------
    # STEP 1: dy/dx = Q/P  ->  u(x, y) = C1
    # -------------------------------------------------

    y_func = sp.Function("y")

    try:
        ode_1 = sp.Eq(
            y_func(x).diff(x),
            (Q / P).subs(y, y_func(x))
        )

        solution_1 = sp.dsolve(ode_1, y_func(x))

    except Exception as error:
        raise ValueError(
            f"Could not solve dy/dx = Q/P: {error}"
        )

    if isinstance(solution_1, list):
        solution_1 = solution_1[0]

    characteristic_1 = solution_1.rhs

    u_expr = _isolate_constant(characteristic_1, y, C1)

    # -------------------------------------------------
    # STEP 2: dz/dx = R/P  (y eliminated via step 1)
    #         -> v(x, y, z) = C2
    # -------------------------------------------------

    characteristic_1_k = characteristic_1.subs(C1, K1)

    z_func = sp.Function("z")

    R_sub = R.subs(y, characteristic_1_k)
    P_sub = P.subs(y, characteristic_1_k)

    if sp.simplify(P_sub) == 0:
        raise ValueError(
            "Could not solve dz/dx = R/P along the first "
            "characteristic curve (division by zero)."
        )

    try:
        ode_2 = sp.Eq(
            z_func(x).diff(x),
            (R_sub / P_sub).subs(z, z_func(x))
        )

        solution_2 = sp.dsolve(ode_2, z_func(x))

    except Exception as error:
        raise ValueError(
            f"Could not solve dz/dx = R/P: {error}"
        )

    if isinstance(solution_2, list):
        solution_2 = solution_2[0]

    # dsolve always names its constant C1; rename to C2
    # so it does not collide with the first invariant.
    characteristic_2 = solution_2.rhs.subs(C1, C2)

    v_expr_k1 = _isolate_constant(characteristic_2, z, C2)

    v_expr = sp.simplify(
        v_expr_k1.subs(K1, u_expr)
    )

    F = sp.Function("F")

    general_solution = sp.Eq(
        F(u_expr, v_expr),
        0
    )

    verified_u = sp.simplify(
        P * sp.diff(u_expr, x)
        + Q * sp.diff(u_expr, y)
    ) == 0

    verified_v = sp.simplify(
        P * sp.diff(v_expr, x)
        + Q * sp.diff(v_expr, y)
        + R * sp.diff(v_expr, z)
    ) == 0

    return {
        "P": P,
        "Q": Q,
        "R": R,
        "u": u_expr,
        "v": v_expr,
        "general_solution": general_solution,
        "verified_u": verified_u,
        "verified_v": verified_v,
        "verified": verified_u and verified_v
    }


# =========================================================
# STANDARD TYPE I:  f(p, q) = 0
# =========================================================

def standard_type_1(f_pq_expression):
    """
    Solve a first-order PDE of the form:

        f(p, q) = 0

    Set p = a, solve for q = phi(a), giving the
    complete integral:

        z = a x + phi(a) y + b
    """

    f_expr = parse_expression(f_pq_expression)

    f_at_a = f_expr.subs(p, a)

    q_solutions = sp.solve(
        sp.Eq(f_at_a, 0),
        q
    )

    if not q_solutions:
        raise ValueError(
            "Could not solve f(p, q) = 0 for q."
        )

    q_of_a = sp.simplify(q_solutions[0])

    z_rhs = a * x + q_of_a * y + b

    complete_integral = sp.Eq(z, z_rhs)

    p_check = sp.diff(z_rhs, x)
    q_check = sp.diff(z_rhs, y)

    verified = (
        sp.simplify(p_check - a) == 0
        and sp.simplify(q_check - q_of_a) == 0
        and sp.simplify(
            f_expr.subs({p: p_check, q: q_check})
        ) == 0
    )

    return {
        "f": f_expr,
        "q_of_a": q_of_a,
        "complete_integral": complete_integral,
        "verified": verified
    }


# =========================================================
# STANDARD TYPE II (CLAIRAUT'S EQUATION):
#     z = px + qy + f(p, q)
# =========================================================

def standard_type_2_clairaut(f_pq_expression):
    """
    Solve Clairaut's equation:

        z = p x + q y + f(p, q)

    The complete integral is obtained directly by
    replacing p -> a and q -> b:

        z = a x + b y + f(a, b)
    """

    f_expr = parse_expression(f_pq_expression)

    f_at_ab = f_expr.subs({p: a, q: b})

    z_rhs = a * x + b * y + f_at_ab

    complete_integral = sp.Eq(z, z_rhs)

    p_check = sp.diff(z_rhs, x)
    q_check = sp.diff(z_rhs, y)

    original_rhs = p * x + q * y + f_expr

    substituted = sp.simplify(
        original_rhs.subs({p: p_check, q: q_check})
        - z_rhs
    )

    verified = substituted == 0

    return {
        "f": f_expr,
        "complete_integral": complete_integral,
        "verified": verified
    }


# =========================================================
# STANDARD TYPE III (SEPARABLE):
#     f(x, p) = g(y, q)
# =========================================================

def standard_type_3_separable(f_xp_expression, g_yq_expression):
    """
    Solve a separable first-order PDE of the form:

        f(x, p) = g(y, q)

    Both sides are set equal to a separation constant a:

        f(x, p) = a  ->  p = phi(x, a)
        g(y, q) = a  ->  q = psi(y, a)

    and integrated to give the complete integral:

        z = int phi(x, a) dx + int psi(y, a) dy + b
    """

    f_expr = parse_expression(f_xp_expression)
    g_expr = parse_expression(g_yq_expression)

    p_solutions = sp.solve(
        sp.Eq(f_expr, a),
        p
    )

    if not p_solutions:
        raise ValueError(
            "Could not solve f(x, p) = a for p."
        )

    p_of_x = sp.simplify(p_solutions[0])

    q_solutions = sp.solve(
        sp.Eq(g_expr, a),
        q
    )

    if not q_solutions:
        raise ValueError(
            "Could not solve g(y, q) = a for q."
        )

    q_of_y = sp.simplify(q_solutions[0])

    z_expr = (
        sp.integrate(p_of_x, x)
        + sp.integrate(q_of_y, y)
        + b
    )

    complete_integral = sp.Eq(z, sp.simplify(z_expr))

    p_check = sp.diff(z_expr, x)
    q_check = sp.diff(z_expr, y)

    verified = (
        sp.simplify(
            f_expr.subs(p, p_check) - a
        ) == 0
        and sp.simplify(
            g_expr.subs(q, q_check) - a
        ) == 0
    )

    return {
        "f": f_expr,
        "g": g_expr,
        "p_of_x": p_of_x,
        "q_of_y": q_of_y,
        "complete_integral": complete_integral,
        "verified": verified
    }


# =========================================================
# STANDARD TYPE IV (x, y ABSENT):
#     f(z, p, q) = 0
# =========================================================

def standard_type_4_no_xy(f_zpq_expression):
    """
    Solve a first-order PDE of the form:

        f(z, p, q) = 0

    with x and y both absent. Substituting
    u = x + a y and treating z as a function of u alone
    (p = dz/du, q = a dz/du) reduces the PDE to a
    separable ODE in z(u), giving the complete integral:

        int dz / phi(z, a) = x + a y + b
    """

    f_expr = parse_expression(f_zpq_expression)

    Zp = sp.Symbol("Zp")

    substituted = f_expr.subs({
        p: Zp,
        q: a * Zp
    })

    zp_solutions = sp.solve(
        sp.Eq(substituted, 0),
        Zp
    )

    if not zp_solutions:
        raise ValueError(
            "Could not solve f(z, p, q) = 0 for dz/du."
        )

    zp_expr = sp.simplify(zp_solutions[0])

    u_from_z = sp.integrate(1 / zp_expr, z)

    implicit_relation = sp.Eq(
        u_from_z,
        x + a * y + b
    )

    implicit_expr = u_from_z - (x + a * y + b)

    dz_denominator = sp.diff(implicit_expr, z)

    verified = False

    if sp.simplify(dz_denominator) != 0:

        p_check = sp.simplify(
            -sp.diff(implicit_expr, x) / dz_denominator
        )

        q_check = sp.simplify(
            -sp.diff(implicit_expr, y) / dz_denominator
        )

        verified = sp.simplify(
            f_expr.subs({p: p_check, q: q_check})
        ) == 0

    return {
        "f": f_expr,
        "dz_du": zp_expr,
        "complete_integral": implicit_relation,
        "verified": verified
    }
