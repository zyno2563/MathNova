/**
 * Entry point for every page except the Solver, which boots itself.
 *
 * Reads `data-page` off <body>, mounts the shared chrome, then runs
 * whatever small behaviour that particular page needs.
 */

import { initHomeDemo } from './home-demo.js';
import { createChat } from './assistant.js';
import { get } from './api.js';
import { SUPPORT_EMAIL } from './pages.js';
import { mountShell } from './shell.js';
import { apply, effective, onChange, stored } from './theme.js';

const page = document.body.dataset.page || '';

// The dedicated assistant page hosts the conversation itself, so it
// does not also get the floating copy of it.
mountShell({ current: page, assistant: page !== 'assistant' });

const initialisers = {
  home: initHomePage,
  assistant: initAssistantPage,
  settings: initSettingsPage,
  contact: initContactPage
};

if (initialisers[page]) initialisers[page]();

/* ==========================================================
   Home
   ========================================================== */

function initHomePage() {
  // The solver used to live at the site root, addressed by a hash —
  // "/#transforms". Those links are in people's bookmarks and notes, so
  // send them on rather than dropping them on a page with a hash that
  // means nothing here.
  const hash = location.hash.replace('#', '').trim();

  if (['fourier-series', 'calculus', 'linear-algebra', 'ode', 'pde', 'numerical', 'transforms'].includes(hash)) {
    location.replace(`/solver/#${hash}`);
    return;
  }
  initHomeDemo();
}

/* ==========================================================
   AI Assistant page
   ========================================================== */

function initAssistantPage() {
  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const send = document.getElementById('chat-send');

  if (!log || !form || !input) return;

  const chat = createChat({ log, form, input, send });

  chat.greet();

  document.querySelectorAll('.suggestion').forEach((button) => {
    button.addEventListener('click', () => {
      input.value = button.dataset.ask || button.textContent.trim();
      input.focus();
      form.requestSubmit();
    });
  });
}

/* ==========================================================
   Settings page
   ========================================================== */

function initSettingsPage() {
  const themeGroup = document.getElementById('theme-choice');

  if (themeGroup) {
    const sync = () => {
      const choice = stored();

      themeGroup.querySelectorAll('button').forEach((button) => {
        button.setAttribute(
          'aria-pressed', String(button.dataset.theme === choice)
        );
      });

      const showing = document.getElementById('theme-showing');
      if (showing) showing.textContent = effective();
    };

    themeGroup.addEventListener('click', (event) => {
      const button = event.target.closest('button[data-theme]');
      if (!button) return;

      apply(button.dataset.theme);
      sync();
    });

    onChange(sync);
    sync();
  }

  reportAssistantStatus();
  wireReset();
}

async function reportAssistantStatus() {
  const target = document.getElementById('assistant-state');

  if (!target) return;

  try {
    const status = await get('/api/assistant/status');

    // Availability only. What runs it is not reported to the browser.
    target.textContent = status.enabled ? 'Available' : 'Unavailable';

    if (!status.enabled && status.message) {
      const hint = document.getElementById('assistant-hint');
      if (hint) {
        hint.textContent = status.message;
        hint.hidden = false;
      }
    }
  } catch (error) {
    target.textContent = 'Could not reach the server';
  }
}

function wireReset() {
  const button = document.getElementById('reset-preferences');
  const note = document.getElementById('reset-note');

  if (!button) return;

  button.addEventListener('click', () => {
    try {
      localStorage.clear();
    } catch (error) {
      // Nothing was stored to begin with.
    }

    apply('system');

    if (note) {
      note.textContent = 'Preferences cleared.';
      note.hidden = false;
    }
  });
}

/* ==========================================================
   Contact page
   ========================================================== */

function initContactPage() {
  const button = document.getElementById('copy-email');
  const note = document.getElementById('copy-note');

  if (!button) return;

  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(SUPPORT_EMAIL);

      if (note) {
        note.textContent = 'Address copied.';
        note.hidden = false;
      }
    } catch (error) {
      // Clipboard access can be refused; the address is on the page in
      // full, so there is nothing to recover from.
      if (note) {
        note.textContent = `Copy it manually: ${SUPPORT_EMAIL}`;
        note.hidden = false;
      }
    }
  });
}
