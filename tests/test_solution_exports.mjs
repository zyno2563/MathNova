import test from 'node:test';
import assert from 'node:assert/strict';
import { answerText, answerLatex, answerKeys, solutionText, verificationText } from '../frontend/js/solution-data.js';
const math = (text, latex = text) => ({ text, latex });
const module = { id: 'linear-algebra', name: 'Linear Algebra' };
const method = { id: 'analyze', label: 'Analyse a matrix' };

test('matrix exports retain exact fractions, eigenvalues, and vectors', () => {
  const result = { determinant: math('1/3', '\\frac{1}{3}'), eigenvectors: [{ eigenvalue: math('2'), vectors: [math('Matrix([[1], [0]])', '\\begin{bmatrix}1\\\\0\\end{bmatrix}')] }] };
  assert.match(answerText(result, module, method), /1\/3/);
  assert.match(answerText(result, module, method), /Matrix\(\[\[1\], \[0\]\]\)/);
  assert.doesNotMatch(answerText(result, module, method), /\[object Object\]/);
  assert.match(answerLatex(result, module, method), /\\frac\{1\}\{3\}/);
  assert.match(answerLatex(result, module, method), /\\begin\{bmatrix\}/);
});

test('inverse Fourier copies the returned function rather than the input transform', () => {
  const result = { direction: 'inverse', f: math('exp(-x)'), F: math('1/(1+w^2)') };
  assert.deepEqual(answerKeys(result, 'transforms', 'fourier'), ['f']);
  assert.equal(answerText(result, { id: 'transforms' }, { id: 'fourier' }), 'f:\nexp(-x)');
});

test('text download carries original input, verification evidence and no plot bulk', () => {
  const result = { determinant: math('3'), verification_checks: [{ label: 'Inverse', verified: true, residual: math('0') }], plot: { x: [999999] } };
  const text = solutionText(result, module, method, { matrix: '2, 1\n1, 2' });
  assert.match(text, /Matrix: 2, 1\n1, 2/);
  assert.match(text, /Inverse: Passed; residual: 0/);
  assert.doesNotMatch(text, /999999/);
});

test('unknown and failed checks cannot export a successful status', () => {
  assert.match(verificationText({}), /Not verified/);
  assert.match(verificationText({ verified: false }), /Did not pass/);
  assert.match(verificationText({ verified: null }), /Not verified/);
});


test('scientific notation is valid mathematical LaTeX', () => {
  const result = { root: 1.2e-7 };
  const tex = answerLatex(result, { id: 'numerical' }, { id: 'root-finding' });
  assert.ok(tex.includes('1.2\\times 10^{-7}'));
  assert.ok(answerLatex({ root: 3e25 }, { id: 'numerical' }, { id: 'root-finding' }).includes('3\\times 10^{25}'));
});
