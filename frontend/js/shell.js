/**
 * The shared chrome: topbar, sidebar navigation, footer, assistant.
 *
 * Every page declares only its own content and lets this build the rest,
 * so navigation is identical everywhere by construction rather than by
 * ten copies being kept in step. The markup it produces matches what the
 * solver already used — same class names, same ids — so the existing
 * stylesheet and the solver's own script keep working untouched.
 */

import { get } from './api.js';
import { initAssistant } from './assistant.js';
import { PRIMARY, SECONDARY, SUPPORT_EMAIL } from './pages.js';
import { effective, onChange, restore, toggle } from './theme.js';

/**
 * Mount the chrome around whatever the page already contains.
 *
 * `current` is the page id, used to mark the active link.
 * `sidebarExtras` is an optional element the page owns — the solver
 * passes its module list so both live in the one drawer on mobile.
 */
export function mountShell({ current, assistant = true } = {}) {
  restore();

  // A page may already carry the chrome (the solver ships its own
  // sidebar markup); only build what is missing.
  if (!document.querySelector('.topbar')) {
    document.body.insertAdjacentHTML('afterbegin', topbarHtml());
  }

  const sidebar = document.getElementById('site-nav');

  if (sidebar) {
    sidebar.insertAdjacentHTML('afterbegin', navHtml(current));
  }

  markCurrent(current);
  wireNavToggle();
  wireThemeToggle();
  mountFooter(current);
  checkHealth();

  if (assistant) {
    mountAssistantPanel();
  }

  registerServiceWorker();
}

/**
 * Make the site installable (and publishable as an Android app).
 *
 * Failure is silent on purpose: the worker only adds an offline page,
 * and the site works exactly as before without it.
 */
function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;

  const register = () =>
    navigator.serviceWorker.register('/sw.js').catch(() => {});

  // After load, so installing it never competes with the first paint —
  // but register immediately if load has already happened.
  if (document.readyState === 'complete') {
    register();
  } else {
    window.addEventListener('load', register, { once: true });
  }
}

/* ---------- markup ---------- */

function topbarHtml() {
  const links = PRIMARY.map(
    (page) =>
      `<a class="toplink" href="${page.href}" data-page="${page.id}">${page.label}</a>`
  ).join('');

  return `
<a class="skip-link" href="#main">Skip to content</a>

<header class="topbar">
  <button class="icon-button nav-toggle" id="nav-toggle"
          aria-label="Toggle navigation" aria-expanded="false" aria-controls="sidebar">
    <span aria-hidden="true">☰</span>
  </button>

  <a class="brand" href="/">
    <span class="brand-mark" aria-hidden="true">∑</span>
    <span class="brand-text">
      <strong>MathNova</strong>
      <small>Engineering Mathematics Engine</small>
    </span>
  </a>

  <nav class="toplinks" aria-label="Primary">${links}</nav>

  <div class="topbar-actions">
    <span class="status-dot" id="api-status" title="Checking API…" aria-live="polite"></span>
    <button class="icon-button" id="theme-toggle" aria-label="Switch colour theme">
      <span aria-hidden="true" id="theme-icon">◐</span>
    </button>
  </div>
</header>`;
}

function navHtml(current) {
  const primary = PRIMARY.map((page) => `
    <li>
      <a href="${page.href}" data-page="${page.id}"
         ${page.id === current ? 'aria-current="page"' : ''}>
        <span class="glyph" aria-hidden="true">${page.glyph}</span>
        <span>${page.label}</span>
      </a>
    </li>`).join('');

  const secondary = SECONDARY.filter(page => current !== 'solver' || !['terms', 'privacy', 'disclaimer'].includes(page.id)).map((page) => `
    <li>
      <a href="${page.href}" data-page="${page.id}"
         ${page.id === current ? 'aria-current="page"' : ''}>${page.label}</a>
    </li>`).join('');

  return `
<p class="nav-heading">Product</p>
<ul class="nav-list">${primary}</ul>

<p class="nav-heading">More</p>
<ul class="nav-list small">${secondary}</ul>`;
}

function footerHtml(current) {
  const links = SECONDARY.concat(PRIMARY.filter((page) => page.id !== 'home'))
    .filter((page) => page.id !== current)
    .map((page) => `<a href="${page.href}">${page.label}</a>`)
    .join('');

  const year = new Date().getFullYear();

  return `
<footer class="site-foot">
  <div class="foot-inner">
    <nav class="foot-links" aria-label="Secondary">${links}</nav>

    <p class="foot-note">
      Found a bug or need help? Email
      <a href="mailto:${SUPPORT_EMAIL}">${SUPPORT_EMAIL}</a>.
      MathNova checks its own results, but always verify anything you
      rely on — see the
      <a href="/disclaimer/">AI &amp; Mathematical Disclaimer</a>.
    </p>

    <p class="foot-meta">© ${year} MathNova · V1 · No account needed</p>
  </div>
</footer>`;
}

/* ---------- behaviour ---------- */

function markCurrent(current) {
  document.querySelectorAll('.toplink').forEach((link) => {
    if (link.dataset.page === current) {
      link.setAttribute('aria-current', 'page');
    }
  });
}

function wireNavToggle() {
  const toggleButton = document.getElementById('nav-toggle');
  const sidebar = document.getElementById('sidebar');
  const scrim = document.getElementById('scrim');

  if (!toggleButton || !sidebar) return;

  // The solver wires its own copy of this; do not double-bind.
  if (toggleButton.dataset.wired) return;
  toggleButton.dataset.wired = 'true';

  const close = () => {
    sidebar.classList.remove('open');
    if (scrim) scrim.hidden = true;
    toggleButton.setAttribute('aria-expanded', 'false');
  };

  toggleButton.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    if (scrim) scrim.hidden = !open;
    toggleButton.setAttribute('aria-expanded', String(open));
  });

  if (scrim) scrim.addEventListener('click', close);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && sidebar.classList.contains('open')) close();
  });

  // Following a link should not leave the drawer covering the page.
  sidebar.addEventListener('click', (event) => {
    if (event.target.closest('a')) close();
  });
}

function wireThemeToggle() {
  const button = document.getElementById('theme-toggle');
  const icon = document.getElementById('theme-icon');

  if (!button || button.dataset.wired) return;
  button.dataset.wired = 'true';

  const sync = () => {
    if (icon) icon.textContent = effective() === 'dark' ? '☀' : '☾';
  };

  sync();
  onChange(sync);

  button.addEventListener('click', () => toggle());
}

function mountFooter(current) {
  if (document.querySelector('.site-foot')) return;

  document.body.insertAdjacentHTML('beforeend', footerHtml(current));
}

async function checkHealth() {
  const dot = document.getElementById('api-status');

  if (!dot) return;

  try {
    const health = await get('/api/health');
    dot.classList.add('online');
    dot.title = `API healthy — v${health.version}`;
  } catch (error) {
    dot.classList.add('offline');
    dot.title = 'API unreachable';
  }
}

/**
 * Add the floating assistant to pages that do not already host it.
 *
 * The dedicated assistant page opts out: a floating button that opens a
 * small copy of the page you are already on helps nobody.
 */
function mountAssistantPanel() {
  if (document.getElementById('assistant-fab')) return;

  document.body.insertAdjacentHTML('beforeend', `
<button class="assistant-fab" id="assistant-fab"
        aria-label="Open the AI Mathematics Assistant">
  <span aria-hidden="true">✦</span>
</button>

<aside class="assistant-panel" id="assistant"
       aria-label="AI Mathematics Assistant" hidden>
  <header class="assistant-head">
    <h2>AI Mathematics Assistant</h2>
    <button class="icon-button" id="assistant-close" aria-label="Close assistant">
      <span aria-hidden="true">✕</span>
    </button>
  </header>

  <div class="assistant-log" id="assistant-log"></div>

  <form class="assistant-form" id="assistant-form">
    <label class="sr-only" for="assistant-input">Ask a question</label>
    <textarea id="assistant-input" rows="2"
      placeholder="Ask anything — e.g. “Find the Laplace transform of t²e^(−3t)”"></textarea>
    <button type="submit" class="button primary" id="assistant-send">Send</button>
  </form>
</aside>`);

  // The page may name the context it is in, so the assistant knows what
  // the reader is looking at.
  initAssistant(() => window.mathnovaContext && window.mathnovaContext());
}
