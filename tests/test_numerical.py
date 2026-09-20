from core.numerical.root_finding import (
    bisection,
    newton_raphson,
    secant
)

from core.numerical.differentiation import (
    forward_difference,
    backward_difference,
    central_difference,
    second_derivative_central
)

from core.numerical.integration import (
    trapezoidal_rule,
    simpsons_one_third_rule,
    simpsons_three_eighth_rule
)

from core.numerical.interpolation import (
    lagrange_interpolation,
    newton_divided_difference
)

from core.numerical.linear_systems import (
    gauss_elimination,
    jacobi_iteration,
    gauss_seidel
)


# =========================================================
# ROOT FINDING
# =========================================================

def test_bisection():
    result = bisection("x^3 - x - 2", 1, 2)

    print("\nBisection Method")
    print("-----------------")
    print("Root:", result["root"])
    print("Iterations:", result["iterations_count"])
    print("Verified:", result["verified"])

    assert result["verified"]
    assert abs(result["root"] - 1.5213797) < 1e-4


def test_bisection_no_sign_change_raises():
    try:
        bisection("x^2 + 1", 0, 1)
        raised = False

    except ValueError:
        raised = True

    assert raised


def test_newton_raphson():
    result = newton_raphson("x^3 - x - 2", 1.5)

    print("\nNewton-Raphson Method")
    print("----------------------")
    print("Root:", result["root"])
    print("Iterations:", result["iterations_count"])
    print("Verified:", result["verified"])

    assert result["verified"]
    assert abs(result["root"] - 1.5213797) < 1e-4


def test_secant():
    result = secant("x^3 - x - 2", 1.0, 2.0)

    print("\nSecant Method")
    print("--------------")
    print("Root:", result["root"])
    print("Iterations:", result["iterations_count"])
    print("Verified:", result["verified"])

    assert result["verified"]
    assert abs(result["root"] - 1.5213797) < 1e-4


# =========================================================
# NUMERICAL DIFFERENTIATION
# =========================================================

def test_forward_difference():
    result = forward_difference("x^3 - x - 2", 2.0)

    print("\nForward Difference")
    print("--------------------")
    print("Approx:", result["approx_derivative"])
    print("Exact:", result["exact_derivative"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_backward_difference():
    result = backward_difference("x^3 - x - 2", 2.0)

    print("\nBackward Difference")
    print("---------------------")
    print("Approx:", result["approx_derivative"])
    print("Exact:", result["exact_derivative"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_central_difference():
    result = central_difference("x^3 - x - 2", 2.0)

    print("\nCentral Difference")
    print("--------------------")
    print("Approx:", result["approx_derivative"])
    print("Exact:", result["exact_derivative"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_second_derivative_central():
    result = second_derivative_central("x^3 - x - 2", 2.0)

    print("\nSecond Derivative (Central)")
    print("-----------------------------")
    print("Approx:", result["approx_second_derivative"])
    print("Exact:", result["exact_second_derivative"])
    print("Verified:", result["verified"])

    assert result["verified"]


# =========================================================
# NUMERICAL INTEGRATION
# =========================================================

def test_trapezoidal_rule():
    result = trapezoidal_rule("x^3 - x - 2", 0, 1, 10)

    print("\nTrapezoidal Rule")
    print("------------------")
    print("Integral:", result["integral"])
    print("Exact:", result["exact_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_simpsons_one_third_rule():
    result = simpsons_one_third_rule("x^3 - x - 2", 0, 1, 10)

    print("\nSimpson's 1/3 Rule")
    print("--------------------")
    print("Integral:", result["integral"])
    print("Exact:", result["exact_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]
    assert abs(result["integral"] - result["exact_integral"]) < 1e-8


def test_simpsons_three_eighth_rule():
    result = simpsons_three_eighth_rule("x^3 - x - 2", 0, 1, 9)

    print("\nSimpson's 3/8 Rule")
    print("--------------------")
    print("Integral:", result["integral"])
    print("Exact:", result["exact_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]
    assert abs(result["integral"] - result["exact_integral"]) < 1e-8


def test_simpsons_one_third_requires_even_n():
    try:
        simpsons_one_third_rule("x^2", 0, 1, 5)
        raised = False

    except ValueError:
        raised = True

    assert raised


# =========================================================
# INTERPOLATION
# =========================================================

def test_lagrange_interpolation():
    x_values = [0, 1, 2, 3]
    y_values = [1, 2, 9, 28]

    result = lagrange_interpolation(
        x_values,
        y_values,
        x_eval=1.5
    )

    print("\nLagrange Interpolation")
    print("------------------------")
    print("Polynomial:", result["polynomial"])
    print("Verified:", result["verified"])
    print("y(1.5):", result["y_eval"])

    assert result["verified"]
    assert abs(result["y_eval"] - 4.375) < 1e-9


def test_lagrange_interpolation_float_inputs():
    # Regression test: float x/y values (as produced by
    # UI text-input parsing) must not leave floating-point
    # noise (e.g. a spurious 1e-15 x^2 term) that breaks
    # exact verification.
    x_values = [0.0, 1.0, 2.0, 3.0]
    y_values = [1.0, 2.0, 9.0, 28.0]

    result = lagrange_interpolation(
        x_values,
        y_values,
        x_eval=1.5
    )

    print("\nLagrange Interpolation — Float Inputs")
    print("----------------------------------------")
    print("Polynomial:", result["polynomial"])
    print("Verified:", result["verified"])

    assert result["verified"]

    import sympy as sp
    from core.numerical.utils import x as x_sym

    assert sp.expand(
        result["polynomial"] - (x_sym ** 3 + 1)
    ) == 0


def test_newton_divided_difference():
    x_values = [0, 1, 2, 3]
    y_values = [1, 2, 9, 28]

    result = newton_divided_difference(
        x_values,
        y_values,
        x_eval=1.5
    )

    print("\nNewton's Divided Difference")
    print("------------------------------")
    print("Polynomial:", result["polynomial"])
    print("Verified:", result["verified"])
    print("y(1.5):", result["y_eval"])

    assert result["verified"]
    assert abs(result["y_eval"] - 4.375) < 1e-9


def test_interpolation_methods_agree():
    x_values = [0, 1, 2, 3]
    y_values = [1, 2, 9, 28]

    lagrange_result = lagrange_interpolation(
        x_values,
        y_values
    )

    newton_result = newton_divided_difference(
        x_values,
        y_values
    )

    print("\nInterpolation Cross-Check")
    print("----------------------------")
    print("Lagrange:", lagrange_result["polynomial"])
    print("Newton:", newton_result["polynomial"])

    assert (
        lagrange_result["polynomial"]
        == newton_result["polynomial"]
    )


# =========================================================
# LINEAR SYSTEMS
# =========================================================

def test_gauss_elimination():
    A = [[4, 1, 2], [3, 5, 1], [1, 1, 3]]
    b = [4, 7, 3]

    result = gauss_elimination(A, b)

    print("\nGauss Elimination")
    print("--------------------")
    print("Solution:", result["solution"])
    print("Verified:", result["verified"])

    assert result["verified"]

    for value, expected in zip(
        result["solution"],
        [0.5, 1.0, 0.5]
    ):
        assert abs(value - expected) < 1e-6


def test_jacobi_iteration():
    A = [[4, 1, 2], [3, 5, 1], [1, 1, 3]]
    b = [4, 7, 3]

    result = jacobi_iteration(A, b)

    print("\nJacobi Iteration")
    print("-------------------")
    print("Solution:", result["solution"])
    print("Iterations:", result["iterations_count"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_gauss_seidel():
    A = [[4, 1, 2], [3, 5, 1], [1, 1, 3]]
    b = [4, 7, 3]

    result = gauss_seidel(A, b)

    print("\nGauss-Seidel Iteration")
    print("-------------------------")
    print("Solution:", result["solution"])
    print("Iterations:", result["iterations_count"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_jacobi_non_dominant_raises():
    A = [[1, 2, 3], [2, 1, 3], [3, 3, 1]]
    b = [6, 6, 7]

    try:
        jacobi_iteration(A, b, max_iterations=50)
        raised = False

    except ValueError:
        raised = True

    assert raised


def test_gauss_elimination_singular_raises():
    A = [[1, 2], [2, 4]]
    b = [3, 6]

    try:
        gauss_elimination(A, b)
        raised = False

    except ValueError:
        raised = True

    assert raised


if __name__ == "__main__":
    test_bisection()
    test_bisection_no_sign_change_raises()
    test_newton_raphson()
    test_secant()

    test_forward_difference()
    test_backward_difference()
    test_central_difference()
    test_second_derivative_central()

    test_trapezoidal_rule()
    test_simpsons_one_third_rule()
    test_simpsons_three_eighth_rule()
    test_simpsons_one_third_requires_even_n()

    test_lagrange_interpolation()
    test_newton_divided_difference()
    test_interpolation_methods_agree()

    test_gauss_elimination()
    test_jacobi_iteration()
    test_gauss_seidel()
    test_jacobi_non_dominant_raises()
    test_gauss_elimination_singular_raises()
