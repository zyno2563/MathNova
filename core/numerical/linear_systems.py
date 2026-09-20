import numpy as np


def _verify_solution(A, b, solution, tolerance=1e-6):
    """
    Independently verify a computed solution against
    NumPy's own linear solver (numpy.linalg.solve).
    """

    try:
        reference = np.linalg.solve(A, b)

        return bool(
            np.allclose(
                solution,
                reference,
                atol=max(tolerance * 100, 1e-4)
            )
        )

    except Exception:
        return False


def gauss_elimination(matrix_a, vector_b):
    """
    Solve Ax = b using Gaussian elimination with
    partial pivoting, followed by back substitution.
    """

    A = np.array(matrix_a, dtype=float)
    b = np.array(vector_b, dtype=float)

    n = len(b)

    if A.shape != (n, n):
        raise ValueError(
            "A must be a square matrix matching the "
            "length of b."
        )

    augmented = np.hstack([A.copy(), b.reshape(-1, 1)])

    steps = []

    for pivot_index in range(n):

        max_row = (
            np.argmax(
                np.abs(augmented[pivot_index:, pivot_index])
            )
            + pivot_index
        )

        if augmented[max_row, pivot_index] == 0:
            raise ValueError(
                "Matrix is singular; no unique solution "
                "exists."
            )

        if max_row != pivot_index:
            augmented[[pivot_index, max_row]] = (
                augmented[[max_row, pivot_index]]
            )

        for row in range(pivot_index + 1, n):

            factor = (
                augmented[row, pivot_index]
                / augmented[pivot_index, pivot_index]
            )

            augmented[row] -= (
                factor * augmented[pivot_index]
            )

        steps.append(augmented.copy())

    solution = np.zeros(n)

    for row in range(n - 1, -1, -1):

        solution[row] = (
            augmented[row, -1]
            - np.dot(
                augmented[row, row + 1:n],
                solution[row + 1:n]
            )
        ) / augmented[row, row]

    return {
        "A": A,
        "b": b,
        "upper_triangular_steps": [
            step.tolist() for step in steps
        ],
        "solution": solution.tolist(),
        "verified": _verify_solution(A, b, solution)
    }


def jacobi_iteration(
    matrix_a,
    vector_b,
    initial_guess=None,
    tolerance=1e-6,
    max_iterations=100
):
    """
    Solve Ax = b using the Jacobi iterative method:

        x_i^(k+1) = (b_i - sum_(j != i) a_ij x_j^(k))
                    / a_ii

    Converges reliably when A is diagonally dominant.
    """

    A = np.array(matrix_a, dtype=float)
    b = np.array(vector_b, dtype=float)

    n = len(b)

    if A.shape != (n, n):
        raise ValueError(
            "A must be a square matrix matching the "
            "length of b."
        )

    if np.any(np.diag(A) == 0):
        raise ValueError(
            "Jacobi iteration requires non-zero "
            "diagonal entries."
        )

    x_current = (
        np.zeros(n)
        if initial_guess is None
        else np.array(initial_guess, dtype=float)
    )

    iterations = []

    for iteration in range(1, max_iterations + 1):

        x_next = np.zeros(n)

        for i in range(n):

            other_terms = (
                np.dot(A[i, :], x_current)
                - A[i, i] * x_current[i]
            )

            x_next[i] = (
                b[i] - other_terms
            ) / A[i, i]

        error = np.linalg.norm(
            x_next - x_current,
            ord=np.inf
        )

        iterations.append({
            "iteration": iteration,
            "x": x_next.tolist(),
            "error": float(error)
        })

        x_current = x_next

        if error < tolerance:
            break

    else:
        raise ValueError(
            "Jacobi iteration did not converge within "
            "the maximum number of iterations."
        )

    return {
        "A": A,
        "b": b,
        "solution": x_current.tolist(),
        "iterations": iterations,
        "iterations_count": len(iterations),
        "verified": _verify_solution(A, b, x_current)
    }


def gauss_seidel(
    matrix_a,
    vector_b,
    initial_guess=None,
    tolerance=1e-6,
    max_iterations=100
):
    """
    Solve Ax = b using the Gauss-Seidel iterative
    method:

        x_i^(k+1) = (b_i
                     - sum_(j<i) a_ij x_j^(k+1)
                     - sum_(j>i) a_ij x_j^(k)) / a_ii

    Converges reliably when A is diagonally dominant.
    """

    A = np.array(matrix_a, dtype=float)
    b = np.array(vector_b, dtype=float)

    n = len(b)

    if A.shape != (n, n):
        raise ValueError(
            "A must be a square matrix matching the "
            "length of b."
        )

    if np.any(np.diag(A) == 0):
        raise ValueError(
            "Gauss-Seidel iteration requires non-zero "
            "diagonal entries."
        )

    x_current = (
        np.zeros(n)
        if initial_guess is None
        else np.array(initial_guess, dtype=float)
    )

    iterations = []

    for iteration in range(1, max_iterations + 1):

        x_next = x_current.copy()

        for i in range(n):

            sum_before = np.dot(
                A[i, :i],
                x_next[:i]
            )

            sum_after = np.dot(
                A[i, i + 1:],
                x_current[i + 1:]
            )

            x_next[i] = (
                b[i] - sum_before - sum_after
            ) / A[i, i]

        error = np.linalg.norm(
            x_next - x_current,
            ord=np.inf
        )

        iterations.append({
            "iteration": iteration,
            "x": x_next.tolist(),
            "error": float(error)
        })

        x_current = x_next

        if error < tolerance:
            break

    else:
        raise ValueError(
            "Gauss-Seidel iteration did not converge "
            "within the maximum number of iterations."
        )

    return {
        "A": A,
        "b": b,
        "solution": x_current.tolist(),
        "iterations": iterations,
        "iterations_count": len(iterations),
        "verified": _verify_solution(A, b, x_current)
    }
