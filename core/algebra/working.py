"""Problem-specific matrix working and scoped, independently checked identities."""
import sympy as sp


def matrix_working(matrix, inverse_value=None, eigenspaces=None):
    steps = []
    checks = []

    def step(title, explanation, expression):
        # Pickling an unevaluated numerical equality can reduce it to True.
        # Preserve its display form before crossing the worker boundary.
        if isinstance(expression, sp.Equality):
            expression = {"text": sp.sstr(expression), "latex": sp.latex(expression)}
        steps.append(dict(title=title, explanation=explanation, expression=expression))

    def check(label, residual):
        residual = sp.simplify(residual)
        entries = list(residual) if isinstance(residual, sp.MatrixBase) else [residual]
        zeros = [entry.is_zero for entry in entries]
        verified = True if all(z is True for z in zeros) else (
            False if any(z is False for z in zeros) else None)
        checks.append(dict(label=label, verified=verified, residual=residual))

    reduced, pivots = matrix.rref()
    step('Reduce A to row echelon form',
         f'The reduced matrix has {len(pivots)} pivot columns, so rank(A) = {len(pivots)}.', reduced)
    if matrix.rows == matrix.cols:
        if matrix.rows == 2:
            a, b, c, d = list(matrix)
            determinant_expression = sp.Add(sp.Mul(a, d, evaluate=False),
                                            sp.Mul(-1, sp.Mul(b, c, evaluate=False), evaluate=False), evaluate=False)
            step('Calculate det(A) = ad − bc', 'Substitute the four entries of A.',
                 sp.Eq(determinant_expression, matrix.det(), evaluate=False))
        lam = sp.Symbol('lambda')
        polynomial = matrix.charpoly(lam).as_expr()
        step('Form the characteristic equation',
             'Solve det(λI − A) = 0. Its roots are the eigenvalues, counted with multiplicity.',
             sp.Eq(polynomial, 0, evaluate=False))
        if inverse_value is not None:
            augmented = matrix.row_join(sp.eye(matrix.rows))
            step('Row-reduce [A | I] to [I | A⁻¹]',
                 'The right-hand block of this reduced augmented matrix is the inverse.', augmented.rref()[0])
            check('Inverse: A A⁻¹ − I = 0', matrix * inverse_value - sp.eye(matrix.rows))
        for value, multiplicity, vectors in eigenspaces or []:
            step(f'Solve (A − λI)v = 0 for λ = {value}',
                 'Use the nullspace of this reduced matrix; choose nonzero free-variable vectors.',
                 (matrix - value * sp.eye(matrix.rows)).rref()[0])
            check(f'Characteristic polynomial at λ = {value}', polynomial.subs(lam, value))
            for index, vector in enumerate(vectors, 1):
                step(f'Eigenvector {index} for λ = {value}',
                     'A nonzero vector in the nullspace.', vector)
                check(f'Eigenvector {index}, λ = {value}: Av − λv = 0', matrix * vector - value * vector)
    return {'worked_steps': steps, 'verification_checks': checks}
