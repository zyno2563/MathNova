/** Pure formatting shared by on-screen results and portable exports. */
const ANSWERS = {
  'calculus:differentiate': ['simplified'], 'calculus:integrate': ['with_constant'],
  'calculus:evaluate': ['exact', 'numeric'],
  'ode:cf': ['complementary_function'], 'ode:pi': ['pi', 'particular_integral'],
  'ode:complete': ['complete_solution'], 'ode:first-order': ['solution', 'general_solution'],
  'pde:formation': ['pde'], 'pde:lagrange': ['general_solution', 'u', 'v'],
  'pde:standard-type': ['complete_integral', 'solution'],
  'numerical:root-finding': ['root'], 'numerical:differentiation': ['approximate', 'exact'],
  'numerical:integration': ['integral', 'exact_integral'],
  'numerical:interpolation': ['polynomial', 'y_eval'],
  'numerical:linear-system': ['solution'],
  'linear-algebra:analyze': ['matrix', 'rank', 'determinant', 'inverse', 'eigenvalues', 'eigenvectors'],
  'fourier-series:series': ['a0', 'harmonics']
};

export function answerKeys(result, moduleId, methodId) {
  return (ANSWERS[`${moduleId}:${methodId}`] || (
    (methodId.includes('inverse') || result.direction === 'inverse') ? ['f', 'x_n'] :
    methodId.includes('property') ? ['theorem_result', 'initial_value', 'final_value', 'F', 'X'] : ['F', 'Fs', 'Fc', 'X']
  )).filter(k => result[k] !== undefined && result[k] !== null);
}

export function label(key) {
  return ({ a0: 'a₀', an: 'aₙ', bn: 'bₙ', f: 'f', F: 'F', X: 'X(z)', x_n: 'x(n)', Fs: 'Fₛ(ω)', Fc: 'F꜀(ω)' })[key] || key.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
}

export function plainValue(value) {
  if (value === null || value === undefined) return 'Not available';
  if (typeof value !== 'object') return String(value);
  if (typeof value.text === 'string' && typeof value.latex === 'string') return value.text;
  if (Array.isArray(value)) return value.map(plainValue).join('\n');
  return Object.entries(value).map(([k, v]) => `${label(k)}: ${plainValue(v)}`).join('\n');
}

export function answerText(result, module, method) {
  return answerKeys(result, module.id, method.id).map(k => `${method.labels?.[k] || label(k)}:\n${plainValue(result[k])}`).join('\n\n');
}

function latexValue(value, name) {
  // Labels are comments; user text never becomes executable LaTeX commands.
  const comment = `% ${String(name).replace(/[\r\n]/g, ' ')}`;
  if (value && typeof value.latex === 'string') return `${comment}\n\\[${value.latex}\\]`;
  if (typeof value === 'number') {
    const number = String(value).replace(/e([+-]?\d+)$/i, (_, exponent) => `\\times 10^{${Number(exponent)}}`);
    return `${comment}\n\\[${number}\\]`;
  }
  if (Array.isArray(value)) return value.map((v, i) => latexValue(v, `${name} ${i + 1}`)).filter(Boolean).join('\n\n');
  if (value && typeof value === 'object') return Object.entries(value).map(([k, v]) => latexValue(v, `${name}: ${label(k)}`)).filter(Boolean).join('\n\n');
  return `${comment}\n% ${plainValue(value).replace(/[\r\n]/g, ' ')}`;
}

export function answerLatex(result, module, method) {
  return answerKeys(result, module.id, method.id).map(k => latexValue(result[k], method.labels?.[k] || label(k))).join('\n\n');
}

export function verificationText(result) {
  const status = v => v === true ? 'Passed' : v === false ? 'Did not pass' : 'Not verified';
  if (result.verification_checks?.length) return result.verification_checks.map(c => `${c.label}: ${status(c.verified)}; residual: ${plainValue(c.residual)}`).join('\n');
  if (result.verification?.cf) return ['cf', 'pi', 'complete'].map(k => `${k}: ${status(result.verification[k]?.verified)}; residual: ${plainValue(result.verification[k]?.difference)}`).join('\n');
  if ('verified_u' in result || 'verified_v' in result) return `First invariant: ${status(result.verified_u)}\nSecond invariant: ${status(result.verified_v)}`;
  if ('verified' in result) return `Engine check: ${status(result.verified)}${result.verification_description ? '\n' + result.verification_description : ''}`;
  return 'Not verified — no independent check was returned.';
}

export function solutionText(result, module, method, input) {
  // Plot samples are redundant bulk; coefficients and iteration evidence remain.
  const details = Object.fromEntries(Object.entries(result).filter(([k]) => k !== 'plot'));
  return `MathNova — ${module.name} / ${method.label}\n\nINPUT\n${plainValue(input)}\n\nANSWER\n${answerText(result, module, method)}\n\nVERIFICATION\n${verificationText(result)}\n\nCALCULATION DETAILS\n${plainValue(details)}\n\nChecks apply only to the stated identities or numerical comparisons.\n`;
}
