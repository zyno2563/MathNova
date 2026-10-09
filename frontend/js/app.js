/**
 * The Solver page: module navigation, dynamic forms, result rendering.
 *
 * The surrounding chrome — topbar, site navigation, footer, the
 * floating assistant — belongs to shell.js, which every page shares.
 */

import { ApiError, post } from './api.js';
import { MODULES, forcingVisibility } from './modules.js';
import { resultActions } from './result-actions.js';
import { renderSolved } from './results.js';
import { walkthroughFor } from './walkthrough.js';
import { mountShell } from './shell.js';
import { onChange } from './theme.js';
import { alert, clear, el, empty, renderLatex } from './ui.js';

const state = {
  module: MODULES[0],
  method: MODULES[0].methods[0],
  requestId: 0,
  savedResult: null,
  controller: null,
  values: {}
};

const dom = {};

// Which example each method is showing, so the button can move on.
const exampleIndex = new Map();

/* ==========================================================
   Navigation
   ========================================================== */

function buildNav() {
  clear(dom.moduleList);

  for (const module of MODULES) {
    const button = el('button', {
      type: 'button',
      'aria-current': module.id === state.module.id ? 'true' : 'false',
      onClick: () => selectModule(module.id)
    }, [
      el('span', { class: 'glyph', 'aria-hidden': 'true', text: module.glyph }),
      module.name
    ]);

    dom.moduleList.append(el('li', {}, [button]));
  }

}

function selectModule(id) {
  const module = MODULES.find((item) => item.id === id);
  if (!module) return;

  state.module = module;
  state.method = module.methods[0];
  state.values = {};

  location.hash = `#${module.id}`;

  buildNav();
  renderModule();
  closeDrawer();
}


/** Collapse the mobile drawer after a module is chosen. */
function closeDrawer() {
  const sidebar = document.getElementById('sidebar');
  const scrim = document.getElementById('scrim');
  const toggleButton = document.getElementById('nav-toggle');

  if (!sidebar || !sidebar.classList.contains('open')) return;

  sidebar.classList.remove('open');
  if (scrim) scrim.hidden = true;
  if (toggleButton) toggleButton.setAttribute('aria-expanded', 'false');
}

function selectMethod(id) {
  const method = state.module.methods.find((item) => item.id === id);
  if (!method) return;

  state.method = method;
  state.values = {};

  renderModule();
}

/* ==========================================================
   Form
   ========================================================== */

/** Which fields the current values make relevant. */
function visibleFields(method, values) {
  const all = method.fields || [];

  let names = all.map((field) => field.name);

  if (method.visible) {
    const driver = driverField(method);
    const list = driver ? method.visible[values[driver]] : null;
    if (list) names = list;
  }

  // The ODE forcing block has its own dependency rule.
  if (all.some((field) => field.name === 'forcing_type')) {
    const forcing = forcingVisibility(values.forcing_type);
    names = names.filter(
      (name) => !name.startsWith('forcing_') || forcing.includes(name)
    );
  }

  return all.filter((field) => names.includes(field.name));
}

/** The select whose value drives `method.visible`. */
function driverField(method) {
  const candidates = ['method', 'type', 'property', 'rule', 'kind'];
  const names = (method.fields || []).map((field) => field.name);

  return candidates.find((name) => names.includes(name));
}

/**
 * Load the next worked example for this method.
 *
 * The form opens on the first example already, so loading "the
 * example" once looked identical to pressing Compute. Each press now
 * moves to the next one and says which it is.
 */
function loadExample() {
  const walkthrough = walkthroughFor(state.module.id, state.method.id);
  const examples = (walkthrough && walkthrough.examples) || [];

  if (!examples.length) {
    // No curated set: fall back to restoring the method's defaults.
    state.values = defaultValues(state.method);
    renderForm();
    run();
    return;
  }

  const key = `${state.module.id}:${state.method.id}`;

  // Start at the second one: the first is what the form already shows.
  const next = exampleIndex.has(key)
    ? (exampleIndex.get(key) + 1) % examples.length
    : 1 % examples.length;

  exampleIndex.set(key, next);

  const example = examples[next];

  state.values = { ...defaultValues(state.method), ...example.values };

  renderForm();
  announceExample(example, next + 1, examples.length);
  run();
}

function announceExample(example, position, total) {
  if (!dom.exampleNote) return;

  dom.exampleNote.textContent =
    `Example ${position} of ${total} — ${example.label}`;
  dom.exampleNote.hidden = false;
}

function defaultValues(method) {
  const values = {};

  for (const field of method.fields || []) {
    values[field.name] = field.value;
  }

  return values;
}

function renderModule() {
  state.controller?.abort();
  state.controller = null;
  state.requestId++;
  state.savedResult = null;
  dom.inputNotice = null;
  dom.spinner.hidden = true;
  dom.submit.disabled = false;
  dom.cancel.hidden = true;
  dom.requestStatus.hidden = true;
  dom.modulePicker.value = state.module.id;
  dom.title.textContent = state.module.name;
  dom.blurb.textContent = state.module.blurb;

  clear(dom.tabs);

  if (state.module.methods.length > 1) {
    for (const method of state.module.methods) {
      dom.tabs.append(el('button', {
        type: 'button',
        role: 'tab',
        'aria-selected': method.id === state.method.id ? 'true' : 'false',
        onClick: () => selectMethod(method.id)
      }, [method.label]));
    }
  }

  state.values = { ...defaultValues(state.method), ...state.values };

  renderForm();
  clear(dom.results).append(
    empty('Fill in the inputs and press Compute.')
  );
}

function renderForm() {
  const method = state.method;

  clear(dom.form);

  const formula = method.formulaFor
    ? method.formulaFor[state.values[driverField(method)]]
    : method.formula;

  if (formula) {
    dom.formula.hidden = false;
    renderLatex(clear(dom.formula), formula, true);
  } else {
    dom.formula.hidden = true;
  }

  for (const field of visibleFields(method, state.values)) {
    dom.form.append(fieldNode(field));
  }
  updateInputNotice();
}

function fieldNode(field) {
  const id = `field-${field.name}`;
  const value = state.values[field.name];

  let control;

  if (field.type === 'select') {
    control = el('select', { id, name: field.name },
      field.options.map(([optionValue, label]) =>
        el('option', {
          value: optionValue,
          selected: String(optionValue) === String(value)
        }, [label])));
  } else if (field.type === 'textarea') {
    control = el('textarea', { id, name: field.name, rows: 4 });
    control.value = value ?? '';
  } else {
    control = el('input', {
      id,
      name: field.name,
      type: field.type === 'number' ? 'number' : 'text',
      value: value ?? '',
      step: field.step,
      min: field.min,
      max: field.max,
      spellcheck: 'false'
    });
  }

  control.addEventListener('input', () => {
    state.values[field.name] = control.value;
    updateInputNotice();
  });

  if (field.reactive) {
    control.addEventListener('change', () => {
      state.values[field.name] = control.value;

      // Let the method fix up any values the new choice invalidates.
      if (typeof state.method.adjust === 'function') {
        state.method.adjust(state.values, field.name);
      }

      renderForm();
      updateInputNotice();
    });
  }

  return el('div', { class: `field${field.wide ? ' wide' : ''}` }, [
    el('label', { for: id, text: field.label }),
    control,
    field.hint ? el('div', { class: 'hint', text: field.hint }) : null
  ]);
}

/* ==========================================================
   Running a computation
   ========================================================== */

function requestBody() {
  const method = state.method;
  const fields = visibleFields(method, state.values);

  const values = {};

  for (const field of fields) {
    let value = state.values[field.name];

    if (field.type === 'number') {
      value = value === '' || value === null ? null : Number(value);
      if (value !== null && Number.isNaN(value)) value = null;
    }

    values[field.name] = value;
  }

  if (typeof method.build === 'function') return method.build(values);

  const body = {};

  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === '') continue;
    body[key] = value;
  }

  return body;
}

/**
 * Headline the *cause*, not the input. A network failure blamed on the
 * expression sends a student editing maths that was already correct.
 */
function headlineFor(code) {
  if (code === 'server_busy' || code === 'rate_limited') return 'Please try again shortly';
  if (code === 'request_timeout') return 'The server took too long';
  if (code === 'request_cancelled') return 'Calculation cancelled';
  if (code === 'network_error' || code === 'bad_response') {
    return 'Could not reach the server';
  }

  if (code === 'unsolvable') {
    return 'The engine could not solve that';
  }

  if (code === 'invalid_input' || code === 'validation_error') {
    return 'That input could not be solved';
  }

  return 'Something went wrong';
}


/** Keep the answer tied to the request that produced it, even while editing. */
function updateInputNotice() {
  if (!state.savedResult || !dom.inputNotice) return;

  let changed = true;
  try {
    changed = JSON.stringify(requestBody()) !== JSON.stringify(state.savedResult.input);
  } catch {
    // An unfinished edit may not yet be a valid request.
  }
  dom.inputNotice.hidden = !changed;
}

function renderSavedResult({ preserveDisclosures = false } = {}) {
  if (!state.savedResult) return;
  const { result, module, method, input, fields } = state.savedResult;
  const disclosures = preserveDisclosures
    ? [...dom.results.querySelectorAll('details')].map(node => node.open)
    : [];

  clear(dom.results);
  dom.results.append(...resultActions(result, module, method, input));
  dom.inputNotice = el('p', {
    class: 'result-input-notice', role: 'status', 'aria-live': 'polite', hidden: true,
    text: 'Inputs changed — compute again. The result below uses the submitted inputs.'
  });
  dom.results.append(el('details', { class: 'card result-input-context', open: true }, [
    el('summary', { text: 'Inputs used for this result' }),
    el('dl', {}, fields.map(({ label, value }) => el('div', {}, [
      el('dt', { text: label }),
      el('dd', { text: value })
    ])))
  ]), dom.inputNotice);

  const walkthrough = walkthroughFor(module.id, method.id);
  const steps = walkthrough && walkthrough.steps;
  const rendered = renderSolved(result, module, method, steps);
  for (const node of [].concat(rendered)) {
    if (node) dom.results.append(node);
  }
  if (preserveDisclosures) {
    [...dom.results.querySelectorAll('details')].forEach((node, index) => {
      if (index < disclosures.length) node.open = disclosures[index];
    });
  }
  updateInputNotice();
}

async function run() {
  state.controller?.abort();
  const controller = new AbortController();
  state.controller = controller;
  const method = state.method;
  const module = state.module;
  const requestId = ++state.requestId;

  dom.spinner.hidden = false;
  dom.submit.disabled = true;
  dom.cancel.hidden = false;
  dom.requestStatus.hidden = false;
  dom.requestStatus.textContent = 'Calculating…';
  const slowMessage = setTimeout(() => {
    if (requestId !== state.requestId) return;
    dom.requestStatus.textContent = 'The server may be waking up, or this calculation may need more time. You can wait or cancel.';
  }, 8000);

  try {
    const input = requestBody();
    const fields = visibleFields(method, state.values).map(field => ({
      label: field.label,
      value: field.type === 'select'
        ? (field.options.find(([value]) => String(value) === String(state.values[field.name]))?.[1]
          ?? state.values[field.name])
        : String(state.values[field.name] ?? '')
    }));
    const result = await post(method.endpoint, input, { signal: controller.signal });

    if (requestId !== state.requestId || method !== state.method) return;
    state.savedResult = { result, module, method, input, fields };
    renderSavedResult();
    dom.results.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (error) {
    if (requestId !== state.requestId || method !== state.method) return;
    state.savedResult = null;
    dom.inputNotice = null;
    const isApi = error instanceof ApiError;

    clear(dom.results).append(alert(
      'bad',
      isApi ? headlineFor(error.code) : 'Something went wrong',
      isApi ? error.message : String(error)
    ));

    if (!isApi) console.error(error);
  } finally {
    clearTimeout(slowMessage);
    if (requestId === state.requestId) {
      state.controller = null;
      dom.cancel.hidden = true;
      dom.requestStatus.hidden = true;
      dom.spinner.hidden = true;
      dom.submit.disabled = false;
    }
  }
}

/* ==========================================================
   Boot
   ========================================================== */

function cacheDom() {
  dom.moduleList = document.getElementById('module-list');
  dom.modulePicker = document.getElementById('module-picker');
  dom.title = document.getElementById('module-title');
  dom.blurb = document.getElementById('module-blurb');
  dom.tabs = document.getElementById('method-tabs');
  dom.form = document.getElementById('method-form');
  dom.formula = document.getElementById('method-formula');
  dom.results = document.getElementById('results');
  dom.spinner = document.getElementById('spinner');
  dom.submit = document.getElementById('submit-button');
  dom.cancel = document.getElementById('cancel-button');
  dom.requestStatus = document.getElementById('request-status');
  dom.example = document.getElementById('example-button');
  dom.exampleNote = document.getElementById('example-note');
  dom.sidebar = document.getElementById('sidebar');
}

function boot() {
  // Chrome first: the solver's own markup sits inside it, and cacheDom
  // below expects the topbar and drawer to exist.
  mountShell({ current: 'solver' });

  cacheDom();
  dom.cancel.addEventListener('click', () => state.controller?.abort());
  MODULES.forEach(m => dom.modulePicker.append(el('option', { value: m.id, text: m.name })));
  dom.modulePicker.addEventListener('change', () => selectModule(dom.modulePicker.value));

  // Chart colours come from CSS tokens, so a theme swap needs a repaint.
  onChange(() => {
    renderSavedResult({ preserveDisclosures: true });
  });

  const fromHash = MODULES.find(
    (module) => module.id === location.hash.replace('#', '')
  );

  if (fromHash) {
    state.module = fromHash;
    state.method = fromHash.methods[0];
  }

  const matrixPreset = new URL(location.href).searchParams.get('matrix');
  const hasPreset = state.module.id === 'linear-algebra' && matrixPreset && matrixPreset.length <= 4000;
  if (hasPreset) state.values = { matrix: matrixPreset };
  buildNav();
  renderModule();
  if (hasPreset) run();

  dom.form.addEventListener('submit', (event) => {
    event.preventDefault();
    run();
  });

  dom.example.addEventListener('click', loadExample);

  window.addEventListener('hashchange', () => {
    const module = MODULES.find(
      (item) => item.id === location.hash.replace('#', '')
    );
    if (module && module.id !== state.module.id) selectModule(module.id);
  });

  // Tell the shared assistant which module the reader is looking at.
  window.mathnovaContext = () => state.module.name;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
