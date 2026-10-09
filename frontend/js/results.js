/** Answer-first presentation. Verification only reflects checks actually returned. */
import { card, el, mathRow, stats, isMath, badge, formatNumber, alert } from './ui.js';
import { answerKeys, label } from './solution-data.js';
import { renderGeneric, renderSteps } from './modules.js';

export function disclosure(title, nodes) {
  return el('details', { class: 'card result-details' }, [
    el('summary', { text: title }), el('div', { class: 'card-body' }, nodes)
  ]);
}

function status(value, numerical = false) {
  return badge(value === true ? 'good' : 'warn', value === true
    ? (numerical ? 'Numerically checked' : 'Verified')
    : value === false ? 'Check did not pass' : 'Not verified');
}

export function verificationReport(result, moduleId, methodId) {
  const checks = [];
  const numerical = moduleId === 'numerical' && methodId !== 'interpolation';
  const add = (label, verified, evidence) => {
    const content = [el('p', { text: label }), status(verified, numerical)];
    for (const [name, value] of Object.entries(evidence || {})) {
      if (isMath(value)) content.push(mathRow(name, value));
      else if (typeof value === 'number') content.push(stats([[name, formatNumber(value)]]));
    }
    checks.push(el('div', { class: 'verification-check' }, [status(verified, numerical), disclosure(label + ' — show check', content)]));
  };
  if (Array.isArray(result.verification_checks)) {
    result.verification_checks.forEach(c => add(c.label, c.verified, { Residual: c.residual }));
  } else if (result.verification?.cf) {
    for (const [key, label] of [['cf', 'Complementary function'], ['pi', 'Particular integral'], ['complete', 'Complete solution']]) {
      const c = result.verification[key];
      if (c) add(`${label}: substitute into the differential equation`, c.verified, { Residual: c.difference });
    }
  } else if ('verified_u' in result || 'verified_v' in result) {
    add('First invariant', result.verified_u);
    add('Second invariant', result.verified_v);
  } else if ('verified' in result) {
    add(result.verification_description || (numerical ? 'Numerical engine check (not an exact proof)' : 'Engine verification'), result.verified,
      { Residual: result.residual, Difference: result.difference, Tolerance: result.tolerance });
    if (result.verification && typeof result.verification === 'object') {
      for (const [key, value] of Object.entries(result.verification)) {
        if (isMath(value)) checks.push(mathRow(key.replaceAll('_', ' '), value));
      }
    }
    if (!('residual' in result) && !('difference' in result)) {
      checks.push(el('p', { class: 'hint', text: 'The engine reports this status but does not supply a residual for this method.' }));
    }
  }
  if (!checks.length) {
    checks.push(status(null), el('p', { text: 'No independent verification was returned for this calculation.' }));
  }
  if (result.accuracy) {
    checks.push(el('p', { text: 'The error at one sample point describes the truncated Fourier approximation; it does not verify every coefficient or the whole curve.' }),
      stats([['Sample x', formatNumber(result.accuracy.at_x)], ['Absolute approximation error', formatNumber(result.accuracy.absolute_error)]]));
  }
  if (moduleId === 'linear-algebra') checks.push(el('p', { class: 'hint', text: 'Each status applies only to its labelled identity. It is not a separate verification of every reported quantity.' }));
  return card('Verification', checks);
}

export function renderSolved(result, module, method, steps) {
  let answers, extras = [];
  if (method.render) {
    answers = [].concat(method.render(result));
    if (module.id === 'fourier-series') {
      extras = [answers[0]]; // graph after the answer and its checks
      answers = answers.slice(1);
    } else if (module.id === 'numerical') {
      extras = answers.slice(1);
      answers = answers.slice(0, 1);
    }
  } else {
    const keys = answerKeys(result, module.id, method.id);
    const values = keys.filter(k => result[k] !== undefined && result[k] !== null)
      .map(k => mathRow(method.labels?.[k] || label(k), result[k]));
    answers = [values.length ? card('Answer', values) : renderGeneric(result, method.labels)];
    if (values.length) extras.push(disclosure('Additional calculation details', [renderGeneric(result, method.labels)]));
  }
  let worked;
  if (result.worked_steps?.length) {
    worked = el('ol', { class: 'steps' }, result.worked_steps.map(s => el('li', { class: 'step' }, [
      el('h4', { class: 'step-title', text: s.title }),
      el('p', { class: 'step-explain', text: s.explanation }), mathRow('', s.expression)
    ])));
  } else if (result.worked_steps_error) {
    worked = alert('warn', 'Worked steps unavailable', result.worked_steps_error);
  } else if (steps) {
    worked = renderSteps(result, steps, method.labels)?.card;
  }
  return [...answers, verificationReport(result, module.id, method.id),
    ...(worked ? [disclosure('Worked steps for this problem', [worked])] : []), ...extras];
}
