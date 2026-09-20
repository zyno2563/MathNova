from core.calculus.calculus import (
    differentiate,
    integrate,
    evaluate
)


def test_calculus():

    expression = "x^3 + 2*x"

    derivative = differentiate(
        expression
    )

    integral = integrate(
        expression
    )

    value = evaluate(
        expression,
        2
    )

    print("\nCalculus Test")
    print("-------------")

    print(
        "Expression:",
        expression
    )

    print(
        "Derivative:",
        derivative
    )

    print(
        "Integral:",
        integral
    )

    print(
        "f(2):",
        value
    )


if __name__ == "__main__":
    test_calculus()