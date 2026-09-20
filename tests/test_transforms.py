import sympy as sp

from core.transforms.utils import t as t_symbol

from core.transforms.laplace import (
    laplace_transform,
    inverse_laplace_transform,
    first_shifting_theorem,
    second_shifting_theorem,
    derivative_property,
    integral_property,
    multiplication_by_t,
    division_by_t
)

from core.transforms.fourier_transform import (
    fourier_transform,
    inverse_fourier_transform,
    fourier_sine_transform,
    inverse_fourier_sine_transform,
    fourier_cosine_transform,
    inverse_fourier_cosine_transform,
    shifting_property as fourier_shifting_property,
    scaling_property as fourier_scaling_property
)

from core.transforms.z_transform import (
    z_transform,
    inverse_z_transform,
    linearity_property as z_linearity_property,
    scaling_theorem as z_scaling_theorem,
    time_shifting_theorem,
    initial_value_theorem,
    final_value_theorem
)


# =========================================================
# LAPLACE TRANSFORM
# =========================================================

def test_laplace_transform_sine():
    result = laplace_transform("sin(t)")

    print("\nLaplace Transform of sin(t)")
    print("-----------------------------")
    print("F(s):", result["F"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_inverse_laplace_transform():
    result = inverse_laplace_transform("1/(s^2+1)")

    print("\nInverse Laplace Transform")
    print("---------------------------")
    print("f(t):", result["f"])
    print("Verified:", result["verified"])

    assert result["verified"]
    assert result["f"] == sp.sin(t_symbol)


def test_first_shifting_theorem():
    result = first_shifting_theorem("sin(t)", 3)

    print("\nFirst Shifting Theorem")
    print("-------------------------")
    print("Direct:", result["direct_transform"])
    print("Theorem:", result["theorem_result"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_second_shifting_theorem():
    result = second_shifting_theorem("t^2", 2)

    print("\nSecond Shifting Theorem")
    print("--------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_derivative_property_first_order():
    result = derivative_property("sin(t)", order=1)

    print("\nDerivative Property (Order 1)")
    print("--------------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_derivative_property_second_order():
    result = derivative_property("sin(t)", order=2)

    print("\nDerivative Property (Order 2)")
    print("--------------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_derivative_property_invalid_order_raises():
    try:
        derivative_property("sin(t)", order=3)
        raised = False

    except ValueError:
        raised = True

    assert raised


def test_integral_property():
    result = integral_property("sin(t)")

    print("\nIntegral Property")
    print("--------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_multiplication_by_t():
    result = multiplication_by_t("exp(-2*t)", power=2)

    print("\nMultiplication by t^n")
    print("------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_division_by_t():
    result = division_by_t("sin(t)")

    print("\nDivision by t")
    print("----------------")
    print("Verified:", result["verified"])

    assert result["verified"]


# =========================================================
# FOURIER TRANSFORM
# =========================================================

def test_fourier_transform_gaussian():
    result = fourier_transform("exp(-x^2)")

    print("\nFourier Transform of a Gaussian")
    print("----------------------------------")
    print("F(w):", result["F"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_fourier_sine_transform_round_trip():
    forward = fourier_sine_transform("exp(-2*x)")

    print("\nFourier Sine Transform Round Trip")
    print("------------------------------------")
    print("Fs(w):", forward["Fs"])
    print("Forward verified:", forward["verified"])

    assert forward["verified"]

    backward = inverse_fourier_sine_transform(
        str(forward["Fs"])
    )

    print("Recovered f(x):", backward["f"])
    print("Backward verified:", backward["verified"])

    assert backward["verified"]


def test_fourier_cosine_transform_round_trip():
    forward = fourier_cosine_transform("exp(-2*x)")

    print("\nFourier Cosine Transform Round Trip")
    print("--------------------------------------")
    print("Fc(w):", forward["Fc"])
    print("Forward verified:", forward["verified"])

    assert forward["verified"]

    backward = inverse_fourier_cosine_transform(
        str(forward["Fc"])
    )

    print("Recovered f(x):", backward["f"])
    print("Backward verified:", backward["verified"])

    assert backward["verified"]


def test_fourier_shifting_property():
    result = fourier_shifting_property("exp(-x^2)", 1)

    print("\nFourier Shifting Property")
    print("----------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_fourier_scaling_property():
    result = fourier_scaling_property("exp(-x^2)", 2)

    print("\nFourier Scaling Property")
    print("---------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_fourier_scaling_property_zero_raises():
    try:
        fourier_scaling_property("exp(-x^2)", 0)
        raised = False

    except ValueError:
        raised = True

    assert raised


# =========================================================
# Z-TRANSFORM
# =========================================================

def test_z_transform_unit_step():
    result = z_transform("1")

    print("\nZ-Transform of Unit Step")
    print("----------------------------")
    print("X(z):", result["X"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_transform_exponential():
    result = z_transform("a^n")

    print("\nZ-Transform of a^n")
    print("----------------------")
    print("X(z):", result["X"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_transform_n_times_a_n():
    result = z_transform("n*a^n")

    print("\nZ-Transform of n a^n")
    print("------------------------")
    print("X(z):", result["X"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_transform_cosine():
    result = z_transform("cos(n*theta)")

    print("\nZ-Transform of cos(n theta)")
    print("-------------------------------")
    print("X(z):", result["X"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_transform_sine():
    result = z_transform("sin(n*theta)")

    print("\nZ-Transform of sin(n theta)")
    print("-------------------------------")
    print("X(z):", result["X"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_inverse_z_transform_distinct_poles():
    result = inverse_z_transform("z/((z-1)*(z-2))")

    print("\nInverse Z-Transform (Distinct Poles)")
    print("-----------------------------------------")
    print("x(n):", result["x_n"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_inverse_z_transform_repeated_pole():
    result = inverse_z_transform("z/(z-1)^2")

    print("\nInverse Z-Transform (Repeated Pole)")
    print("----------------------------------------")
    print("x(n):", result["x_n"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_transform_and_inverse_are_consistent():
    forward = z_transform("2**n")

    print("\nZ-Transform / Inverse Consistency")
    print("-------------------------------------")
    print("X(z):", forward["X"])

    backward = inverse_z_transform(str(forward["X"]))

    print("Recovered x(n):", backward["x_n"])
    print("Verified:", backward["verified"])

    assert backward["verified"]


def test_z_linearity_property():
    result = z_linearity_property("a**n", "b**n", 2, 3)

    print("\nZ-Transform Linearity")
    print("-------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_scaling_theorem():
    result = z_scaling_theorem("n", 3)

    print("\nZ-Transform Scaling Theorem")
    print("-------------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_time_shifting_theorem():
    result = time_shifting_theorem("a**n", 2)

    print("\nZ-Transform Time Shifting Theorem")
    print("--------------------------------------")
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_initial_value_theorem():
    result = initial_value_theorem("z/(z-2)")

    print("\nZ-Transform Initial Value Theorem")
    print("--------------------------------------")
    print("Initial value:", result["initial_value"])
    print("Verified:", result["verified"])

    assert result["verified"]


def test_z_final_value_theorem():
    result = final_value_theorem("z/(z-0.5)")

    print("\nZ-Transform Final Value Theorem")
    print("------------------------------------")
    print("Final value:", result["final_value"])
    print("Verified:", result["verified"])

    assert result["verified"]


if __name__ == "__main__":
    test_laplace_transform_sine()
    test_inverse_laplace_transform()
    test_first_shifting_theorem()
    test_second_shifting_theorem()
    test_derivative_property_first_order()
    test_derivative_property_second_order()
    test_derivative_property_invalid_order_raises()
    test_integral_property()
    test_multiplication_by_t()
    test_division_by_t()

    test_fourier_transform_gaussian()
    test_fourier_sine_transform_round_trip()
    test_fourier_cosine_transform_round_trip()
    test_fourier_shifting_property()
    test_fourier_scaling_property()
    test_fourier_scaling_property_zero_raises()

    test_z_transform_unit_step()
    test_z_transform_exponential()
    test_z_transform_n_times_a_n()
    test_z_transform_cosine()
    test_z_transform_sine()
    test_inverse_z_transform_distinct_poles()
    test_inverse_z_transform_repeated_pole()
    test_z_transform_and_inverse_are_consistent()
    test_z_linearity_property()
    test_z_scaling_theorem()
    test_z_time_shifting_theorem()
    test_z_initial_value_theorem()
    test_z_final_value_theorem()
