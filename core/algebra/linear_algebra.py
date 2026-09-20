import sympy as sp


def create_matrix(matrix_data):
    """
    Create a SymPy matrix from nested lists.
    """

    return sp.Matrix(matrix_data)


def parse_matrix(matrix_text):
    """
    Convert text input into a SymPy matrix.

    Example:
        2, 1
        1, 2
    """

    rows = []

    for line in matrix_text.strip().splitlines():

        values = [
            value.strip()
            for value in line.split(",")
        ]

        rows.append([
            sp.sympify(value)
            for value in values
        ])

    if not rows:
        raise ValueError("Matrix cannot be empty.")

    column_count = len(rows[0])

    if any(len(row) != column_count for row in rows):
        raise ValueError(
            "All matrix rows must have the same number of columns."
        )

    return sp.Matrix(rows)


def determinant(matrix):
    """
    Calculate the determinant of a square matrix.
    """

    return matrix.det()


def inverse(matrix):
    """
    Calculate the inverse of a square matrix.
    """

    return matrix.inv()


def eigenvalues(matrix):
    """
    Calculate the eigenvalues of a square matrix.
    """

    return matrix.eigenvals()


def eigenvectors(matrix):
    """
    Calculate eigenvalues and eigenvectors.
    """

    return matrix.eigenvects()