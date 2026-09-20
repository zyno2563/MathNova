import numpy as np
from scipy.integrate import quad


def calculate_coefficients(function, L, N):
    """
    Calculate Fourier series coefficients for a function
    with period 2L.

    Parameters:
        function: The function f(x)
        L: Half of the period
        N: Number of Fourier terms

    Returns:
        a0: Constant coefficient
        an: Cosine coefficients
        bn: Sine coefficients
    """

    a0 = (1 / L) * quad(function, -L, L, limit=200)[0]

    an = []
    bn = []

    for n in range(1, N + 1):

        cosine = lambda x: (
            function(x) * np.cos(n * np.pi * x / L)
        )

        sine = lambda x: (
            function(x) * np.sin(n * np.pi * x / L)
        )

        a_n = (1 / L) * quad(cosine, -L, L, limit=200)[0]
        b_n = (1 / L) * quad(sine, -L, L, limit=200)[0]

        an.append(a_n)
        bn.append(b_n)

    return a0, an, bn


def evaluate_series(x, L, a0, an, bn):
    """
    Evaluate the Fourier series at a given x value.

    Parameters:
        x: Point at which to evaluate
        L: Half of the period
        a0: Constant coefficient
        an: Cosine coefficients
        bn: Sine coefficients

    Returns:
        Fourier series approximation at x
    """

    result = a0 / 2

    for n in range(1, len(an) + 1):

        result += (
            an[n - 1] * np.cos(n * np.pi * x / L)
            + bn[n - 1] * np.sin(n * np.pi * x / L)
        )

    return result


def calculate_absolute_error(actual, approximation):
    """
    Calculate the absolute error between
    the actual value and the approximation.
    """

    return abs(actual - approximation)