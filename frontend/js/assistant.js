/**
 * AI Mathematics Assistant panel.
 *
 * Replies arrive as markdown-ish text with $…$ / $$…$$ maths, which is
 * rendered with KaTeX. Everything else is escaped before it reaches
 * the DOM.
 */

import { ApiError, get, post } from './api.js';
import { el } from './ui.js';

const history = [];

// Populated from /api/assistant/status: {enabled, message}. That is all
// the server reports — the provider and model behind it are deployment
// details and are deliberately not exposed.
let status = null;
let busy = false;
let greeted = false;

/* ---------- rendering ---------- */

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderMath(latex, displayMode) {
  if (!window.katex) {
    return `<code>${escapeHtml(latex)}</code>`;
  }

  try {
    return window.katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      output: 'html'
    });
  } catch (error) {
    return `<code>${escapeHtml(latex)}</code>`;
  }
}

/**
 * Pull code and maths out into placeholders, run light markdown over
 * what is left, then put the rendered fragments back.
 */
export function renderRich(source) {
  const slots = [];
  const stash = (html) => {
    slots.push(html);
    return `\u0000${slots.length - 1}\u0000`;
  };

  let text = String(source);

  text = text.replace(/```([\s\S]*?)```/g, (_, code) =>
    stash(`<pre><code>${escapeHtml(code.trim())}</code></pre>`));

  text = text.replace(/`([^`\n]+)`/g, (_, code) =>
    stash(`<code>${escapeHtml(code)}</code>`));

  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex) =>
    stash(renderMath(latex.trim(), true)));

  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, latex) =>
    stash(renderMath(latex.trim(), true)));

  text = text.replace(/\$([^$\n]+?)\$/g, (_, latex) =>
    stash(renderMath(latex.trim(), false)));

  text = text.replace(/\\\(([\s\S]+?)\\\)/g, (_, latex) =>
    stash(renderMath(latex.trim(), false)));

  text = escapeHtml(text);

  text = text.replace(/^### (.*)$/gm, '<h4>$1</h4>');
  text = text.replace(/^## (.*)$/gm, '<h4>$1</h4>');
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

  const blocks = text.split(/\n{2,}/).map((block) => {
    const lines = block.split('\n').filter((line) => line.trim());

    if (lines.length && lines.every((line) => /^\s*[-*]\s+/.test(line))) {
      const items = lines
        .map((line) => `<li>${line.replace(/^\s*[-*]\s+/, '')}</li>`)
        .join('');
      return `<ul>${items}</ul>`;
    }

    if (lines.length && lines.every((line) => /^\s*\d+[.)]\s+/.test(line))) {
      const items = lines
        .map((line) => `<li>${line.replace(/^\s*\d+[.)]\s+/, '')}</li>`)
        .join('');
      return `<ol>${items}</ol>`;
    }

    if (/^<(h4|pre|ul|ol)/.test(block.trim())) return block;

    return `<p>${lines.join('<br>')}</p>`;
  });

  let html = blocks.join('');

  html = html.replace(/\u0000(\d+)\u0000/g, (_, index) => slots[Number(index)]);

  return html;
}

/* ---------- chat core ---------- */

/**
 * Wire a set of chat elements to the assistant endpoint.
 *
 * Both surfaces use this: the floating panel and the full-page
 * assistant. Only the chrome around it differs, so only the chrome is
 * written twice.
 */
export function createChat({ log, form, input, send, getContext }) {
  const history = [];
  let busy = false;
  let greeted = false;

  function bubble(role, html, tools) {
    // The role must stay namespaced behind the msg-- prefix. A bare
    // role class collided with the panel's component rule and turned
    // every message into a fixed, full-height overlay that covered
    // the close button and the input box.
    const node = el('div', { class: `msg msg--${role}` }, [
      el('div', { class: 'who', text: role === 'user' ? 'You' : 'Assistant' }),
      el('div', { class: 'bubble', html })
    ]);

    if (tools && tools.length) {
      node.querySelector('.bubble').append(
        el('div', { class: 'tool-chips' },
          tools.map((name) => el('span', { class: 'tool-chip', text: name })))
      );
    }

    log.append(node);
    log.scrollTop = log.scrollHeight;
    return node;
  }

  async function greet() {
    // Guard on a flag, not on the log being empty: the status call is
    // awaited, so a quick second open would otherwise queue a duplicate
    // greeting before the first one has rendered.
    if (greeted) return;
    greeted = true;

    if (status === null) {
      try {
        status = await get('/api/assistant/status');
      } catch (error) {
        status = { enabled: false, message: null };
      }
    }

    if (status.enabled) {
      // No backend is named. Which model answers is a deployment
      // detail, and the server does not report it.
      bubble('assistant', renderRich(
        'Ask me anything in engineering mathematics. I can run the ' +
        'MathNova engines directly — transforms, ODEs, integrals, ' +
        'eigenvalues and more — so the results are the verified ones.' +
        '\n\n' +
        'Try: *Find the Laplace transform of $t^2e^{-3t}$*'
      ));
    } else {
      bubble('assistant', renderRich(
        '**The assistant is unavailable.**\n\n' +
        (status.message || 'Please try again later.') +
        '\n\nEvery other MathNova module works without it.'
      ));
    }
  }

  async function ask(message) {
    if (!message || busy) return;

    bubble('user', renderRich(message));

    busy = true;
    if (send) send.disabled = true;

    const pending = bubble(
      'assistant',
      '<span class="typing"><i></i><i></i><i></i></span>'
    );

    try {
      const result = await post('/api/assistant/chat', {
        message,
        history: history.slice(-12),
        module: getContext ? getContext() : null
      });

      pending.querySelector('.bubble').innerHTML = renderRich(result.reply);

      if (result.tools_used && result.tools_used.length) {
        pending.querySelector('.bubble').append(
          el('div', { class: 'tool-chips' },
            result.tools_used.map((name) =>
              el('span', { class: 'tool-chip', text: `⚙ ${name}` })))
        );
      }

      history.push({ role: 'user', content: message });
      history.push({ role: 'assistant', content: result.reply });
    } catch (error) {
      const detail = error instanceof ApiError
        ? error.message
        : 'Something went wrong talking to the assistant.';

      pending.querySelector('.bubble').innerHTML =
        `<p><strong>Couldn’t answer.</strong></p><p>${escapeHtml(detail)}</p>`;
    } finally {
      busy = false;
      if (send) send.disabled = false;
      log.scrollTop = log.scrollHeight;
      if (input) input.focus();
    }
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();

    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    ask(message);
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  return { greet, ask, bubble };
}

/* ---------- floating panel ---------- */

export function initAssistant(getModuleContext) {
  const panel = document.getElementById('assistant');
  const fab = document.getElementById('assistant-fab');
  const closeButton = document.getElementById('assistant-close');

  const chat = createChat({
    log: document.getElementById('assistant-log'),
    form: document.getElementById('assistant-form'),
    input: document.getElementById('assistant-input'),
    send: document.getElementById('assistant-send'),
    getContext: getModuleContext
  });

  const input = document.getElementById('assistant-input');

  function open() {
    panel.hidden = false;
    input.focus();
    chat.greet();
  }

  function close() {
    panel.hidden = true;
    fab.focus();
  }

  fab.addEventListener('click', () => (panel.hidden ? open() : close()));
  closeButton.addEventListener('click', close);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) close();
  });

  return { open, close };
}
