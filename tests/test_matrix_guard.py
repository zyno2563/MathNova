"""Matrix resource limits must protect workers without losing completed answers."""

import pytest
import sympy as sp
from fastapi.testclient import TestClient

from backend import errors
from backend.compute import ComputationTimeout, ComputationTooLarge
from backend.main import app
from backend.routers import linear_algebra


client = TestClient(app)


def test_rank_and_eigenvalues_execute_inside_the_guard(monkeypatch):
    inside_guard = False
    operations = []
    original_rank = sp.MutableDenseMatrix.rank
    original_eigenvalues = linear_algebra.eigenvalues

    def guarded(function, *args, **kwargs):
        nonlocal inside_guard
        operations.append(function.__name__)
        inside_guard = True
        try:
            return function(*args, **kwargs)
        finally:
            inside_guard = False

    def checked_rank(matrix, *args, **kwargs):
        assert inside_guard, "Matrix rank bypassed resource isolation"
        return original_rank(matrix, *args, **kwargs)

    def checked_eigenvalues(matrix):
        assert inside_guard, "Eigenvalues bypassed resource isolation"
        return original_eigenvalues(matrix)

    monkeypatch.setattr(errors, "run_guarded", guarded)
    monkeypatch.setattr(sp.MutableDenseMatrix, "rank", checked_rank)
    monkeypatch.setattr(linear_algebra, "eigenvalues", checked_eigenvalues)

    response = client.post("/api/linear-algebra/analyze", json={
        "matrix": "2, 1\n1, 2"
    })

    assert response.status_code == 200, response.text
    assert response.json()["result"]["rank"] == 2
    assert {"checked_rank", "checked_eigenvalues", "determinant", "inverse",
            "eigenvectors", "matrix_working"} <= set(operations)


@pytest.mark.parametrize("matrix, rank, determinant", [
    ("2, 1\n1, 2", 2, "3"),
    ("1, 2, 3\n2, 4, 6", 1, None),
])
@pytest.mark.parametrize("failure", [ComputationTimeout, ComputationTooLarge])
def test_optional_working_limit_preserves_answers(
    monkeypatch, matrix, rank, determinant, failure
):
    def limited(function, *args, **kwargs):
        if function is linear_algebra.matrix_working:
            raise failure()
        return function(*args, **kwargs)

    monkeypatch.setattr(errors, "run_guarded", limited)
    response = client.post("/api/linear-algebra/analyze", json={"matrix": matrix})

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["rank"] == rank
    if determinant is not None:
        assert result["determinant"]["text"] == determinant
        assert result["inverse"]
        assert result["eigenvalues"]
        assert result["eigenvectors"]
    assert result["worked_steps"] == []
    assert "was stopped" in result["worked_steps_error"]
    assert len(result["verification_checks"]) == 1
    check = result["verification_checks"][0]
    assert "unavailable" in check["label"]
    assert check["verified"] is None
    assert check["residual"] is None


@pytest.mark.parametrize("operation", ["inverse", "eigenvalues", "eigenvectors"])
def test_optional_answer_timeout_is_honestly_reported(monkeypatch, operation):
    def limited(function, *args, **kwargs):
        if function is getattr(linear_algebra, operation):
            raise ComputationTimeout()
        return function(*args, **kwargs)

    monkeypatch.setattr(errors, "run_guarded", limited)
    response = client.post("/api/linear-algebra/analyze", json={
        "matrix": "2, 1\n1, 2"
    })

    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["determinant"]["text"] == "3"
    assert result["rank"] == 2
    assert result[operation] is None
    assert "took too long" in result[f"{operation}_error"]
    assert "no inverse" not in result.get("inverse_error", "")


@pytest.mark.parametrize("matrix", ["2, 1\n1, 2", "1, 2, 3\n2, 4, 6"])
def test_required_rank_timeout_has_controlled_error(monkeypatch, matrix):
    def limited(function, *args, **kwargs):
        if function.__name__ == "rank":
            raise ComputationTimeout()
        return function(*args, **kwargs)

    monkeypatch.setattr(errors, "run_guarded", limited)
    response = client.post("/api/linear-algebra/analyze", json={"matrix": matrix})

    assert response.status_code == 503
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "computation_too_expensive"
    assert "rank" in payload["error"]["message"]
