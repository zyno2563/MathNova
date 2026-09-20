from core.algebra.linear_algebra import (
    create_matrix,
    determinant,
    inverse,
    eigenvalues,
    eigenvectors
)


def test_linear_algebra():

    matrix = create_matrix([
        [2, 1],
        [1, 2]
    ])

    print("\nLinear Algebra Test")
    print("-------------------")

    print("\nMatrix:")
    print(matrix)

    print("\nDeterminant:")
    print(determinant(matrix))

    print("\nInverse:")
    print(inverse(matrix))

    print("\nEigenvalues:")
    print(eigenvalues(matrix))

    print("\nEigenvectors:")
    print(eigenvectors(matrix))


if __name__ == "__main__":
    test_linear_algebra()