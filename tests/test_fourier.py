import numpy as np

from core.fourier.series import (
    calculate_coefficients,
    evaluate_series,
    calculate_absolute_error
)


def test_x_function():

    L = np.pi
    function = lambda x: x

    x = L / 2

    actual = function(x)

    print("\nFourier Series Convergence")
    print("--------------------------")

    for N in [1, 2, 5, 10, 20, 50, 100]:

        a0, an, bn = calculate_coefficients(
            function,
            L,
            N
        )

        approximation = evaluate_series(
            x,
            L,
            a0,
            an,
            bn
        )

        error = calculate_absolute_error(
            actual,
            approximation
        )

        print(
            f"N = {N:3d} | "
            f"Approximation = {approximation:.10f} | "
            f"Error = {error:.10f}"
        )


if __name__ == "__main__":
    test_x_function()