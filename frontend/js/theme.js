/**
 * Colour theme, shared by every page.
 *
 * Three states: `light`, `dark`, and `system` (no attribute set, so the
 * stylesheet's prefers-color-scheme rules decide). The choice is stored
 * per browser and applied before anything renders.
 */

const KEY = 'mathnova-theme';

const listeners = new Set();

/** Read the stored choice, tolerating a browser that blocks storage. */
export function stored() {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'light' || value === 'dark' ? value : 'system';
  } catch (error) {
    return 'system';
  }
}

/** Which theme is actually showing right now. */
export function effective() {
  const chosen = document.documentElement.getAttribute('data-theme');

  if (chosen === 'light' || chosen === 'dark') return chosen;

  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

/** Apply a choice and remember it. `system` clears the override. */
export function apply(choice) {
  if (choice === 'light' || choice === 'dark') {
    document.documentElement.setAttribute('data-theme', choice);
  } else {
    document.documentElement.removeAttribute('data-theme');
  }

  try {
    if (choice === 'system') {
      localStorage.removeItem(KEY);
    } else {
      localStorage.setItem(KEY, choice);
    }
  } catch (error) {
    // A browser with storage blocked still gets the theme for this
    // page view; only the memory of it is lost.
  }

  listeners.forEach((listener) => listener(effective()));
}

/** Flip between light and dark, resolving `system` to what is showing. */
export function toggle() {
  apply(effective() === 'dark' ? 'light' : 'dark');
}

/** Run `listener` whenever the effective theme changes. */
export function onChange(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Apply the stored choice. Safe to call more than once. */
export function restore() {
  const choice = stored();

  if (choice !== 'system') {
    document.documentElement.setAttribute('data-theme', choice);
  }

  // Following the system means following it as it changes.
  window
    .matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change', () => {
      if (stored() === 'system') {
        listeners.forEach((listener) => listener(effective()));
      }
    });
}
