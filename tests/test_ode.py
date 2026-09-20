from core.ode.constant_coeff import (
    complementary_function,
    particular_integral_exponential,
    particular_integral_trigonometric,
    particular_integral_polynomial,
    particular_integral_exponential_function,
    build_complete_solution,
    verify_ode_solution
)


def test_distinct_real_roots():
    coefficients = [1, -3, 2]

    auxiliary_equation, roots, cf = (
        complementary_function(
            coefficients
        )
    )

    print("\nCase 1 — Distinct Real Roots")
    print("-----------------------------")

    print(
        "Auxiliary Equation:",
        auxiliary_equation
    )

    print(
        "Roots:",
        roots
    )

    print(
        "CF:",
        cf
    )


def test_repeated_real_roots():
    coefficients = [1, -4, 4]

    auxiliary_equation, roots, cf = (
        complementary_function(
            coefficients
        )
    )

    print("\nCase 2 — Repeated Real Root")
    print("----------------------------")

    print(
        "Auxiliary Equation:",
        auxiliary_equation
    )

    print(
        "Roots:",
        roots
    )

    print(
        "CF:",
        cf
    )


def test_complex_roots():
    coefficients = [1, 0, 4]

    auxiliary_equation, roots, cf = (
        complementary_function(
            coefficients
        )
    )

    print("\nCase 3 — Complex Roots")
    print("----------------------")

    print(
        "Auxiliary Equation:",
        auxiliary_equation
    )

    print(
        "Roots:",
        roots
    )

    print(
        "CF:",
        cf
    )


def test_exponential_pi():
    coefficients = [1, -3, 2]

    a = 4

    result = particular_integral_exponential(
        coefficients,
        a
    )

    print("\nPI — Exponential")
    print("----------------")

    print(
        "Operator:",
        result["operator"]
    )

    print(
        "F(a):",
        result["F_a"]
    )

    print(
        "Resonance:",
        result["resonance"]
    )

    print(
        "PI:",
        result["pi"]
    )


def test_exponential_pi_resonance():
    coefficients = [1, -3, 2]

    a = 1

    result = particular_integral_exponential(
        coefficients,
        a
    )

    print("\nPI — Exponential Resonance")
    print("--------------------------")

    print(
        "Operator:",
        result["operator"]
    )

    print(
        "F(a):",
        result["F_a"]
    )

    print(
        "Resonance:",
        result["resonance"]
    )

    print(
        "Multiplicity:",
        result["multiplicity"]
    )

    print(
        "F derivative at a:",
        result["derivative_at_a"]
    )

    print(
        "PI:",
        result["pi"]
    )


def test_sine_pi():
    coefficients = [1, -3, 2]

    a = 2

    result = particular_integral_trigonometric(
        coefficients,
        a,
        "sin"
    )

    print("\nPI — Sine")
    print("----------")

    print(
        "Operator:",
        result["operator"]
    )

    print(
        "F(ia):",
        result["F_ia"]
    )

    print(
        "Resonance:",
        result["resonance"]
    )

    print(
        "PI:",
        result["pi"]
    )


def test_cosine_pi():
    coefficients = [1, -3, 2]

    a = 2

    result = particular_integral_trigonometric(
        coefficients,
        a,
        "cos"
    )

    print("\nPI — Cosine")
    print("------------")

    print(
        "Operator:",
        result["operator"]
    )

    print(
        "F(ia):",
        result["F_ia"]
    )

    print(
        "Resonance:",
        result["resonance"]
    )

    print(
        "PI:",
        result["pi"]
    )


def test_polynomial_pi():
    coefficients = [1, -3, 2]

    forcing = "x^2"

    result = particular_integral_polynomial(
        coefficients,
        forcing
    )

    print("\nPI — Polynomial")
    print("----------------")

    print(
        "Operator:",
        result["original_operator"]
    )

    print(
        "Forcing:",
        result["forcing"]
    )

    print(
        "Polynomial Degree:",
        result["degree"]
    )

    print(
        "Inverse Operator Coefficients:",
        result["inverse_coefficients"]
    )

    print(
        "PI:",
        result["pi"]
    )


def test_exponential_function_pi():
    coefficients = [1, -3, 2]

    a = 4

    function = "x^2"

    result = particular_integral_exponential_function(
        coefficients,
        a,
        function
    )

    print("\nPI — Exponential × Function")
    print("----------------------------")

    print(
        "Original Operator:",
        result["operator"]
    )

    print(
        "Shift:",
        result["shift"]
    )

    print(
        "Shifted Operator:",
        result["shifted_operator"]
    )

    print(
        "V(x):",
        result["forcing_function"]
    )

    print(
        "Inverse Operator Coefficients:",
        result["inverse_coefficients"]
    )

    print(
        "Polynomial PI:",
        result["polynomial_pi"]
    )

    print(
        "PI:",
        result["pi"]
    )


def test_complete_solution_exponential_function():
    coefficients = [1, -3, 2]

    a = 4
    function = "x^2"

    # -----------------------------
    # CF
    # -----------------------------

    auxiliary_equation, roots, cf = (
        complementary_function(
            coefficients
        )
    )

    # -----------------------------
    # PI
    # -----------------------------

    pi_result = (
        particular_integral_exponential_function(
            coefficients,
            a,
            function
        )
    )

    pi = pi_result["pi"]

    # -----------------------------
    # RHS
    # -----------------------------

    forcing = "exp(4*x)*x^2"

    # -----------------------------
    # Complete Solution
    # -----------------------------

    result = build_complete_solution(
        coefficients,
        cf,
        pi,
        forcing
    )

    print("\nComplete ODE Solution")
    print("---------------------")

    print(
        "Auxiliary Equation:",
        auxiliary_equation
    )

    print(
        "Roots:",
        roots
    )

    print(
        "CF:",
        result["cf"]
    )

    print(
        "PI:",
        result["pi"]
    )

    print(
        "Complete Solution:",
        result["complete_solution"]
    )

    print("\nVerification")
    print("------------")

    print(
        "CF Verified:",
        result["cf_verification"]["verified"]
    )

    print(
        "CF Difference:",
        result["cf_verification"]["difference"]
    )

    print(
        "PI Verified:",
        result["pi_verification"]["verified"]
    )

    print(
        "PI Difference:",
        result["pi_verification"]["difference"]
    )

    print(
        "Complete Solution Verified:",
        result["complete_verification"]["verified"]
    )

    print(
        "Complete Difference:",
        result["complete_verification"]["difference"]
    )


if __name__ == "__main__":
    test_distinct_real_roots()
    test_repeated_real_roots()
    test_complex_roots()

    test_exponential_pi()
    test_exponential_pi_resonance()

    test_sine_pi()
    test_cosine_pi()

    test_polynomial_pi()

    test_exponential_function_pi()

    test_complete_solution_exponential_function()