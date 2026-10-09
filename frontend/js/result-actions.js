import { el } from './ui.js';
import { answerText, answerLatex, solutionText, plainValue } from './solution-data.js';

let printDetails = [];
window.addEventListener('beforeprint', () => {
  if (printDetails.length) return;
  printDetails = [...document.querySelectorAll('#results details')].map(node => [node, node.open]);
  printDetails.forEach(([node]) => { node.open = true; });
});
window.addEventListener('afterprint', () => {
  printDetails.forEach(([node, open]) => { node.open = open; });
  printDetails = [];
});

export function resultActions(result, module, method, input) {
  const message = el('p', { class: 'action-status', role: 'status', 'aria-live': 'polite' });
  const manual = el('textarea', { class: 'copy-fallback', readonly: true, hidden: true, 'aria-label': 'Select and copy this result manually', rows: 6 });
  const copy = async (text, success) => {
    try {
      await navigator.clipboard.writeText(text);
      manual.hidden = true;
      message.textContent = success;
    } catch {
      manual.value = text;
      manual.hidden = false;
      manual.focus();
      manual.select();
      message.textContent = 'Clipboard access is unavailable. Copy the selected text below.';
    }
  };
  const button = (text, action) => el('button', { type: 'button', class: 'button ghost', text, onClick: action });
  const download = () => {
    const blob = new Blob([solutionText(result, module, method, input)], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = el('a', { href: url, download: `mathnova-${module.id}-${method.id}.txt` });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    message.textContent = 'Solution download requested.';
  };
  return [el('div', { class: 'result-toolbar' }, [
    el('div', { class: 'result-actions', role: 'group', 'aria-label': 'Copy or export this result' }, [
      button('Copy answer', () => copy(answerText(result, module, method), 'Answer copied.')),
      button('Copy LaTeX', () => copy(answerLatex(result, module, method), 'LaTeX copied.')),
      button('Download solution (.txt)', download),
      button('Print / Save PDF', () => window.print())
    ]), message, manual
  ]), el('section', { class: 'print-context' }, [
    el('h1', { text: `MathNova — ${module.name}` }),
    el('h2', { text: method.label }),
    el('p', { text: 'Inputs used for this result:' }),
    el('pre', { text: plainValue(input) })
  ])];
}
