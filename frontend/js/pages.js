/**
 * The site map.
 *
 * Every navigation surface — the topbar, the sidebar, the mobile
 * drawer and the footer — is generated from this one list, so a page
 * cannot appear in one menu and be missing from another.
 */

/** The address for bug reports and support. Used everywhere it appears. */
export const SUPPORT_EMAIL = 'b66475781@gmail.com';

/** Primary destinations: the product itself. */
export const PRIMARY = [
  {
    id: 'home',
    href: '/',
    label: 'Home',
    glyph: '⌂',
    blurb: 'What MathNova does and where to start.'
  },
  {
    id: 'solver',
    href: '/solver/',
    label: 'Solver',
    glyph: '∑',
    blurb: 'Every engine: transforms, ODEs, PDEs, calculus, matrices, numerical methods.'
  },
  {
    id: 'learn',
    href: '/learn/',
    label: 'Learn',
    glyph: '◈',
    blurb: 'The methods behind the answers, with worked examples.'
  },
  {
    id: 'assistant',
    href: '/assistant/',
    label: 'AI Assistant',
    glyph: '✦',
    blurb: 'Ask in plain English; the verified engines do the mathematics.'
  }
];

/** Secondary destinations: settings, policy, contact. */
export const SECONDARY = [
  { id: 'settings', href: '/settings/', label: 'Settings' },
  { id: 'about', href: '/about/', label: 'About' },
  { id: 'contact', href: '/contact/', label: 'Contact & Support' },
  { id: 'disclaimer', href: '/disclaimer/', label: 'AI & Mathematical Disclaimer' },
  { id: 'terms', href: '/terms/', label: 'Terms & Conditions' },
  { id: 'privacy', href: '/privacy/', label: 'Privacy Policy' }
];

export const ALL = [...PRIMARY, ...SECONDARY];

/** Look up a page by its id. */
export function pageById(id) {
  return ALL.find((page) => page.id === id) || null;
}
