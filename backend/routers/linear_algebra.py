"""Linear algebra endpoints (core.algebra.linear_algebra)."""

from typing import List, Optional, Union

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from backend.errors import InvalidInput, solve
from backend.serialization import serialize, success
from core.algebra.linear_algebra import (
    create_matrix,
    determinant,
    eigenvalues,
    eigenvectors,
    inverse,
    parse_matrix,
)

router = APIRouter(prefix="/linear-algebra", tags=["linear-algebra"])

MAX_DIMENSION = 8


class MatrixRequest(BaseModel):
    """
    A matrix given either as text ("2, 1\\n1, 2") or as nested rows.
    """

    matrix: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Rows separated by newlines, values by commas",
        examples=["2, 1\n1, 2"]
    )
    rows: Optional[List[List[Union[float, int, str]]]] = Field(
        default=None,
        max_length=MAX_DIMENSION,
        description="Alternative to `matrix`: nested row values"
    )

    @model_validator(mode="after")
    def require_one_form(self):
        if not self.matrix and not self.rows:
            raise ValueError("Provide either 'matrix' text or 'rows'")

        # Bound the shape before anything builds a SymPy Matrix from it.
        # The MAX_DIMENSION check in _build runs after construction, so
        # on its own it would let a huge payload be materialised first.
        for row in self.rows or ():
            if len(row) > MAX_DIMENSION:
                raise ValueError(
                    f"At most {MAX_DIMENSION} columns are supported"
                )

            for value in row:
                if isinstance(value, str) and len(value) > 60:
                    raise ValueError(
                        "Each entry must be at most 60 characters"
                    )

        return self


def _build(request: MatrixRequest):
    if request.rows is not None:
        if not request.rows or not request.rows[0]:
            raise InvalidInput("The matrix cannot be empty.")

        width = len(request.rows[0])

        if any(len(row) != width for row in request.rows):
            raise InvalidInput(
                "All matrix rows must have the same number of columns."
            )

        matrix = solve("Reading the matrix", create_matrix, request.rows)
    else:
        matrix = solve("Parsing the matrix", parse_matrix, request.matrix)

    if max(matrix.rows, matrix.cols) > MAX_DIMENSION:
        raise InvalidInput(
            f"Matrices larger than {MAX_DIMENSION}x{MAX_DIMENSION} are "
            "not supported — symbolic eigen-decomposition becomes "
            "intractable beyond that size."
        )

    return matrix


@router.post("/analyze", summary="Determinant, inverse, eigenvalues, eigenvectors")
def analyze(request: MatrixRequest):
    matrix = _build(request)

    result = {
        "matrix": serialize(matrix),
        "shape": {"rows": matrix.rows, "cols": matrix.cols},
        "is_square": matrix.rows == matrix.cols
    }

    if matrix.rows != matrix.cols:
        # A non-square matrix still has a valid shape/echelon story;
        # report that rather than failing the whole request.
        result["note"] = (
            "Determinant, inverse and eigen-decomposition require a "
            "square matrix."
        )
        result["rank"] = int(matrix.rank())
        return success(result)

    result["determinant"] = serialize(
        solve("Computing the determinant", determinant, matrix)
    )
    result["rank"] = int(matrix.rank())

    # Each of these can legitimately fail (singular matrix, unsolvable
    # characteristic polynomial) without invalidating the others.
    try:
        result["inverse"] = serialize(inverse(matrix))
    except Exception as error:  # noqa: BLE001
        result["inverse"] = None
        result["inverse_error"] = f"This matrix has no inverse ({error})."

    try:
        result["eigenvalues"] = [
            {
                "value": serialize(value),
                "multiplicity": int(multiplicity)
            }
            for value, multiplicity in eigenvalues(matrix).items()
        ]
    except Exception as error:  # noqa: BLE001
        result["eigenvalues"] = None
        result["eigenvalues_error"] = str(error)

    try:
        result["eigenvectors"] = [
            {
                "eigenvalue": serialize(value),
                "multiplicity": int(multiplicity),
                "vectors": [serialize(vector) for vector in vectors]
            }
            for value, multiplicity, vectors in eigenvectors(matrix)
        ]
    except Exception as error:  # noqa: BLE001
        result["eigenvectors"] = None
        result["eigenvectors_error"] = str(error)

    return success(result)
