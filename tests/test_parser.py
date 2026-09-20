from core.calculus.parser import parse_function


def test_parser():

    functions = [
        "x",
        "x^2",
        "x^3 + 2*x",
        "sin(x)",
        "cos(2*x)",
        "exp(x)",
        "sqrt(x)",
        "x*sin(x)"
    ]

    for expression in functions:

        function = parse_function(expression)

        print(
            expression,
            "at x=2 →",
            function(2)
        )


if __name__ == "__main__":
    test_parser()