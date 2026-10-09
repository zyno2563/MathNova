/**
 * DOM and maths-rendering helpers shared by every module view.
 */

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);

  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;

    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'html') node.innerHTML = value;
    else if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) node.setAttribute(key, '');
    else node.setAttribute(key, value);
  }

  for (const child of [].concat(children)) {
    if (child === null || child === undefined) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }

  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

/** Render a LaTeX string into a node, degrading to plain text. */
export function renderLatex(target, latex, displayMode = true) {
  if (window.katex) {
    try {
      window.katex.render(latex, target, {
        displayMode,
        throwOnError: false,
        output: 'htmlAndMathml'
      });
      return target;
    } catch (error) {
      /* fall through to plain text */
    }
  }

  target.textContent = latex;
  target.classList.add('plain');
  return target;
}

/** True when a value is the {text, latex} shape the API uses for SymPy objects. */
export function isMath(value) {
  return Boolean(
    value && typeof value === 'object' && typeof value.latex === 'string'
  );
}

/** A labelled block showing one mathematical expression. */
export function mathRow(label, value) {
  const row = el('div', { class: 'result-row' });

  if (label) row.append(el('div', { class: 'label', text: label }));

  const box = el('div', { class: 'math' });

  if (isMath(value)) {
    renderLatex(box, value.latex);
    box.title = value.text;
  } else {
    box.classList.add('plain');
    box.textContent = String(value);
  }

  row.append(box);
  return row;
}

/** A compact key/value tile grid. */
export function stats(entries) {
  const grid = el('div', { class: 'value-grid' });

  for (const [key, value] of entries) {
    if (value === null || value === undefined) continue;

    grid.append(el('div', { class: 'stat' }, [
      el('div', { class: 'k', text: key }),
      el('div', { class: 'v', text: String(value) })
    ]));
  }

  return grid;
}

export function badge(kind, text) {
  return el('span', { class: `badge ${kind}`, text });
}

/**
 * The verification badge the engines feed. `verified` may be true,
 * false, or null when the engine did not attempt a check.
 */
export function verificationBadge(verified, labels = {}) {
  if (verified === true) {
    return badge('good', labels.good || '✓ Symbolically verified');
  }
  if (verified === false) {
    return badge('warn', labels.warn || '⚠ Could not verify automatically');
  }
  return badge('warn', labels.unknown || 'Verification not attempted');
}

export function card(title, children) {
  const body = el('div', { class: 'card-body' }, children);

  return el('section', { class: 'card' }, [
    title ? el('h3', { text: title }) : null,
    body
  ]);
}

/** A scrollable data table. */
export function table(columns, rows) {
  const head = el('thead', {}, [
    el('tr', {}, columns.map((column) => el('th', { text: column.label })))
  ]);

  const body = el('tbody', {}, rows.map((row) =>
    el('tr', {}, columns.map((column) => {
      const raw = typeof column.get === 'function' ? column.get(row) : row[column.key];
      return el('td', { text: formatNumber(raw) });
    }))
  ));

  return el('div', { class: 'table-wrap' }, [el('table', {}, [head, body])]);
}

/** Numbers are shown at a readable precision, not full float noise. */
export function formatNumber(value, digits = 6) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'yes' : 'no';
  if (typeof value !== 'number') return String(value);
  if (!Number.isFinite(value)) return '—';
  if (Number.isInteger(value) && Math.abs(value) < 1e15) return String(value);

  const magnitude = Math.abs(value);

  if (magnitude !== 0 && (magnitude < 1e-4 || magnitude >= 1e8)) {
    return value.toExponential(3);
  }

  return Number(value.toPrecision(digits)).toString();
}

export function alert(kind, title, detail) {
  return el('div', { class: `alert ${kind}` }, [
    el('strong', { text: title }),
    detail ? el('div', { class: 'detail', text: detail }) : null
  ]);
}

export function empty(message) {
  return el('div', { class: 'empty', text: message });
}
