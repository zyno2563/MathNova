from core.pde.first_order import (
    eliminate_arbitrary_constants,
    lagrange_linear_pde,
    standard_type_1,
    standard_type_2_clairaut,
    standard_type_3_separable,
    standard_type_4_no_xy
)


def test_eliminate_two_constants():
    result = eliminate_arbitrary_constants(
        "a*x + a^2*y^2 + b",
        ["a", "b"]
    )

    print("\nFormation of PDE — Two Constants")
    print("---------------------------------")

    print("PDE:", result["pde"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_eliminate_one_constant():
    result = eliminate_arbitrary_constants(
        "a*x + a^2*y",
        ["a"]
    )

    print("\nFormation of PDE — One Constant")
    print("--------------------------------")

    print("PDE:", result["pde"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_eliminate_constants_classic_example():
    result = eliminate_arbitrary_constants(
        "a*x + b*y + a*b",
        ["a", "b"]
    )

    print("\nFormation of PDE — Classic Example")
    print("-----------------------------------")

    print("PDE:", result["pde"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_lagrange_linear_pde():
    result = lagrange_linear_pde(
        "y*z",
        "x*z",
        "x*y"
    )

    print("\nLagrange's Linear PDE")
    print("----------------------")

    print("u:", result["u"])
    print("v:", result["v"])
    print("General Solution:", result["general_solution"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_lagrange_linear_pde_simple():
    result = lagrange_linear_pde(
        "1",
        "1",
        "z"
    )

    print("\nLagrange's Linear PDE — Simple Case")
    print("-------------------------------------")

    print("u:", result["u"])
    print("v:", result["v"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_standard_type_1():
    result = standard_type_1("p*q - 1")

    print("\nStandard Type I — f(p, q) = 0")
    print("-------------------------------")

    print("Complete Integral:", result["complete_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_standard_type_2_clairaut():
    result = standard_type_2_clairaut("p*q")

    print("\nStandard Type II — Clairaut's Equation")
    print("----------------------------------------")

    print("Complete Integral:", result["complete_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_standard_type_3_separable():
    result = standard_type_3_separable(
        "p^2 - x",
        "q - y^2"
    )

    print("\nStandard Type III — Separable")
    print("-------------------------------")

    print("Complete Integral:", result["complete_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_standard_type_4_no_xy():
    result = standard_type_4_no_xy("p*q - z")

    print("\nStandard Type IV — f(z, p, q) = 0")
    print("------------------------------------")

    print("Complete Integral:", result["complete_integral"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_standard_type_1_no_solution_raises():
    try:
        standard_type_1("0*p + 0*q + 1")
        raised = False

    except ValueError:
        raised = True

    assert raised


if __name__ == "__main__":
    test_eliminate_two_constants()
    test_eliminate_one_constant()
    test_eliminate_constants_classic_example()

    test_lagrange_linear_pde()
    test_lagrange_linear_pde_simple()

    test_standard_type_1()
    test_standard_type_2_clairaut()
    test_standard_type_3_separable()
    test_standard_type_4_no_xy()

    test_standard_type_1_no_solution_raises()
