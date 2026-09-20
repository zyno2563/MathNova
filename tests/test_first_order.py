from core.ode.first_order import (
    variable_separable,
    linear_differential_equation,
    bernoulli_equation,
    exact_equation
)


def test_variable_separable():
    result = variable_separable("x", "y^2")

    print("\nVariable Separable")
    print("-------------------")

    print("Solution:", result["solution"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_linear_differential_equation():
    result = linear_differential_equation("2/x", "x^2")

    print("\nLinear Differential Equation")
    print("-----------------------------")

    print("Integrating Factor:", result["integrating_factor"])
    print("Solution:", result["solution"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_bernoulli_equation():
    result = bernoulli_equation("1/x", "x^2", 2)

    print("\nBernoulli's Equation")
    print("---------------------")

    print("Solution:", result["solution"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_exact_equation():
    result = exact_equation(
        "2*x*y + y^2",
        "x^2 + 2*x*y"
    )

    print("\nExact Differential Equation")
    print("----------------------------")

    print("Is Exact:", result["is_exact"])
    print("Solution:", result["solution"])
    print("Verified:", result["verified"])

    assert result["is_exact"]
    assert result["verified"]


def test_exact_equation_not_exact_raises():
    try:
        exact_equation("y", "x^2")
        raised = False

    except ValueError:
        raised = True

    assert raised


if __name__ == "__main__":
    test_variable_separable()
    test_linear_differential_equation()
    test_bernoulli_equation()
    test_exact_equation()
    test_exact_equation_not_exact_raises()
