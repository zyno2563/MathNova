"""Regression checks for the evidence shown beside answers."""
import sympy as sp
from fastapi.testclient import TestClient
from backend.main import app
from core.algebra.working import matrix_working

client = TestClient(app)


def result(matrix):
    response = client.post('/api/linear-algebra/analyze', json={'matrix': matrix})
    assert response.status_code == 200, response.text
    return response.json()['result']


def test_matrix_working_and_independent_residuals():
    data = result('2, 1\n1, 2')
    equation = next(s for s in data['worked_steps'] if 'characteristic' in s['title'])
    assert 'lambda**2 - 4*lambda + 3' in equation['expression']['text']
    determinant_step = next(s for s in data['worked_steps'] if 'ad − bc' in s['title'])
    assert 'Eq(' in determinant_step['expression']['text']
    assert len(data['verification_checks']) == 5
    assert all(c['verified'] is True for c in data['verification_checks'])
    assert data['verification_checks'][0]['residual']['entries'][0][0]['text'] == '0'


def test_wrong_inverse_and_eigenvector_do_not_get_verified():
    matrix = sp.Matrix([[2, 1], [1, 2]])
    data = matrix_working(matrix, sp.eye(2), [(sp.Integer(1), 1, [sp.Matrix([1, 1])])])
    assert data['verification_checks'][0]['verified'] is False
    assert data['verification_checks'][-1]['verified'] is False


def test_unknown_residual_is_not_passed_or_failed():
    a = sp.Symbol('a')
    checks = matrix_working(sp.Matrix([[a]]), sp.eye(1))['verification_checks']
    assert checks[0]['verified'] is None


def test_singular_matrix_omits_inverse_check_but_keeps_eigen_checks():
    data = result('1, 2\n2, 4')
    assert data['inverse'] is None
    assert all(not c['label'].startswith('Inverse:') for c in data['verification_checks'])
    assert all(c['verified'] is True for c in data['verification_checks'])


def test_rectangular_matrix_has_rank_working_without_claiming_verification():
    data = result('1, 2, 3\n2, 4, 6')
    assert data['rank'] == 1
    assert data['worked_steps']
    assert data['verification_checks'] == []


def test_numerical_difference_and_tolerance_match_engine_check():
    response = client.post('/api/numerical/differentiation', json={
        'function': 'x^3', 'x0': 2, 'h': 0.001, 'method': 'forward'})
    data = response.json()['result']
    assert abs(data['difference'] - (data['approximate'] - 12)) < 1e-10
    assert data['tolerance'] == 0.1
    assert data['verified'] == (abs(data['difference']) < data['tolerance'])
