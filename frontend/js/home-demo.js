import { post } from './api.js';
import { el, clear, mathRow, stats, badge, alert } from './ui.js';

export function initHomeDemo() {
  const form = document.getElementById('home-demo-form');
  if (!form) return;
  const input = document.getElementById('demo-matrix');
  const examples = document.getElementById('demo-example');
  const submit = document.getElementById('demo-run');
  const cancel = document.getElementById('demo-cancel');
  const output = document.getElementById('demo-output');
  const full = document.getElementById('demo-full');
  const options = { symmetric: '2, 1\n1, 2', singular: '1, 2\n2, 4', diagonal: '2, 0\n0, 5' };
  let controller;
  cancel.addEventListener('click', () => controller?.abort());
  const updateLink = () => {
    full.href = `/solver/?${new URLSearchParams({ matrix: input.value })}#linear-algebra`;
  };
  const reset = () => {
    clear(output).append(el('p', { class: 'hint', text: 'Run the example to see the answer and its checks.' }));
    updateLink();
  };
  input.addEventListener('input', reset);
  examples.addEventListener('change', () => { input.value = options[examples.value]; reset(); });
  updateLink();
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (controller) return;
    controller = new AbortController();
    submit.disabled = input.disabled = examples.disabled = true;
    cancel.hidden = false;
    submit.textContent = 'Calculating…';
    output.setAttribute('aria-busy', 'true');
    clear(output).append(el('p', { text: 'Calculating the answer and checking the returned eigenvectors…' }));
    const waking = setTimeout(() => {
      output.append(el('p', { class: 'hint', text: 'The server may be waking up or handling another calculation. You can wait or cancel and try again.' }));
    }, 8000);
    try {
      const result = await post('/api/linear-algebra/analyze', { matrix: input.value }, { signal: controller.signal });
      clear(output).append(stats([['Rank', result.rank], ['Determinant', result.determinant?.text ?? 'Not applicable']]));
      for (const eigen of result.eigenvalues || []) output.append(mathRow(`Eigenvalue (multiplicity ${eigen.multiplicity})`, eigen.value));
      if (result.note) output.append(el('p', { text: result.note }));
      if (result.eigenvalues_error) output.append(alert('warn', 'Eigenvalues unavailable', result.eigenvalues_error));
      const checks = result.verification_checks || [];
      const passed = checks.length > 0 && checks.every(c => c.verified === true);
      const failed = checks.some(c => c.verified === false);
      output.append(badge(passed ? 'good' : 'warn', passed ? `${checks.length} checks passed` : failed ? 'Some checks did not pass' : 'Not fully verified'));
      output.append(el('p', { class: 'hint', text: 'Checks apply to the returned matrix identities. Open the full solution to inspect each residual and the worked steps.' }));
    } catch (error) {
      clear(output).append(alert(error.code === 'request_cancelled' ? 'warn' : 'bad',
        error.code === 'request_cancelled' ? 'Request cancelled' : 'Could not calculate this example', error.message));
    } finally {
      clearTimeout(waking);
      controller = null;
      cancel.hidden = true;
      submit.disabled = input.disabled = examples.disabled = false;
      submit.textContent = 'Run live example';
      output.removeAttribute('aria-busy');
    }
  });
}
