/**
 * Declarative definition of every MathNova module.
 *
 * Each method states which endpoint it calls, which fields it needs,
 * and (optionally) how to render its result. `app.js` stays generic.
 */

import { lineChart, token } from './chart.js';
import {
  alert, card, el, empty, formatNumber, isMath,
  mathRow, stats, table, verificationBadge
} from './ui.js';

/* ==========================================================
   Generic result rendering
   ========================================================== */

// Keys worth showing as a rendered equation, in display order.
const MATH_LABELS = [
  ['pde', 'Partial differential equation'],
  ['auxiliary_equation', 'Auxiliary equation'],
  ['complementary_function', 'Complementary function'],
  ['particular_integral', 'Particular integral'],
  ['complete_solution', 'Complete solution'],
  ['general_solution', 'General solution'],
  ['complete_integral', 'Complete integral'],
  ['solution', 'Solution'],
  ['u', 'First invariant  u = c₁'],
  ['v', 'Second invariant  v = c₂'],
  ['integrating_factor', 'Integrating factor'],
  ['input', 'Input'],
  ['derivative', 'Derivative'],
  ['simplified', 'Simplified'],
  ['integral_expr', 'Integral'],
  ['with_constant', 'Result'],
  ['exact', 'Exact value'],
  ['polynomial', 'Interpolating polynomial  P(x)'],
  ['F', 'F(s)'],
  ['f', 'f(t)'],
  ['Fs', 'Fₛ(w)'],
  ['Fc', 'F_c(w)'],
  ['X', 'X(z)'],
  ['x_n', 'x(n)'],
  ['dz_du', 'dz/du'],
  ['theorem_result', 'Result from the theorem'],
  ['direct_transform', 'Computed directly'],
  ['initial_value', 'Initial value  x(0)'],
  ['final_value', 'Final value  limₙ→∞ x(n)'],
  ['determinant', 'Determinant'],
  ['inverse', 'Inverse'],
  ['q_of_a', 'q in terms of a'],
  ['p_of_x', 'p(x, a)'],
  ['q_of_y', 'q(y, a)']
];

// Keys shown as plain numeric tiles.
const STAT_LABELS = [
  ['root', 'Root'],
  ['residual', 'Residual f(root)'],
  ['iterations_count', 'Iterations'],
  ['approximate', 'Approximate'],
  ['exact', 'Exact (symbolic)'],
  ['integral', 'Approximate integral'],
  ['exact_integral', 'Exact integral'],
  ['y_eval', 'P(x) at the evaluation point'],
  ['numeric', 'Numeric value'],
  ['rank', 'Rank'],
  ['h', 'Step size h'],
  ['x0', 'x₀'],
  ['n', 'n'],
  ['a', 'a'],
  ['b', 'b']
];

// Structural noise the generic renderer should not print.
const HIDDEN_KEYS = new Set([
  'verified', 'verified_u', 'verified_v', 'iterations', 'plot',
  'method', 'rule', 'type', 'property', 'kind', 'direction',
  'divided_difference_table', 'coefficients', 'inverse_error',
  'eigenvalues_error', 'eigenvectors_error', 'upper_triangular_steps',
  'x_values', 'y_values', 'points', 'harmonics', 'an', 'bn', 'a0',
  'matrix', 'shape', 'is_square', 'eigenvalues', 'eigenvectors',
  'accuracy', 'entries', 'rows', 'cols', 'constants_solved',
  'derivative_steps', 'inverse_coefficients'
]);

function verificationSection(result) {
  if (!('verified' in result)) return null;

  const badges = [verificationBadge(result.verified)];

  if ('verified_u' in result || 'verified_v' in result) {
    badges.length = 0;
    badges.push(
      verificationBadge(result.verified_u, {
        good: '✓ u verified', warn: '⚠ u unverified'
      }),
      verificationBadge(result.verified_v, {
        good: '✓ v verified', warn: '⚠ v unverified'
      })
    );
  }

  return el('div', { class: 'result-row' }, [
    el('div', { style: 'display:flex;flex-wrap:wrap;gap:8px' }, badges)
  ]);
}

/** Default renderer: equations first, then numbers, then any table. */
/**
 * Render a result generically.
 *
 * `labels` overrides the shared label for a key. Several engines return
 * the same key names — a transform's input is always `f` and its output
 * is always `F` — but the notation differs by transform: Laplace writes
 * f(t) and F(s), Fourier writes f(x) and F(ω). Without an override a
 * Fourier result was captioned in Laplace notation.
 */
export function renderGeneric(result, labels = null) {
  const nodes = [];
  const shown = new Set(HIDDEN_KEYS);

  const caption = (key, fallback) =>
    (labels && labels[key]) || fallback;

  const verification = verificationSection(result);
  if (verification) nodes.push(verification);

  for (const [key, label] of MATH_LABELS) {
    if (isMath(result[key])) {
      nodes.push(mathRow(caption(key, label), result[key]));
      shown.add(key);
    }
  }

  const tiles = [];

  for (const [key, label] of STAT_LABELS) {
    const value = result[key];
    if (value === null || value === undefined) continue;
    if (isMath(value)) continue;
    if (typeof value === 'object') continue;

    tiles.push([label, formatNumber(value)]);
    shown.add(key);
  }

  if (tiles.length) nodes.push(stats(tiles));

  // Anything left that is still a renderable equation.
  for (const [key, value] of Object.entries(result)) {
    if (shown.has(key)) continue;
    if (isMath(value)) {
      nodes.push(mathRow(prettify(key), value));
      shown.add(key);
    }
  }

  if (Array.isArray(result.iterations) && result.iterations.length) {
    nodes.push(iterationTable(result.iterations));
  }

  if (!nodes.length) {
    nodes.push(empty('The engine returned no displayable result.'));
  }

  return card('Result', nodes);
}

function prettify(key) {
  return key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

function iterationTable(iterations) {
  const keys = Object.keys(iterations[0]).filter(
    (key) => typeof iterations[0][key] !== 'object'
  );

  const columns = keys.map((key) => ({ key, label: prettify(key) }));

  return el('div', { class: 'result-row' }, [
    el('div', { class: 'label', text: `Iterations (${iterations.length})` }),
    table(columns, iterations)
  ]);
}

/* ==========================================================
   Field helpers
   ========================================================== */

const expr = (name, label, value, hint, wide = false) =>
  ({ name, label, type: 'text', value, hint, wide });

const num = (name, label, value, extra = {}) =>
  ({ name, label, type: 'number', value, step: 'any', ...extra });

/* ==========================================================
   Modules
   ========================================================== */

export const MODULES = [
  /* ------------------------------------------------ Fourier */
  {
    id: 'fourier-series',
    name: 'Fourier Series',
    glyph: '∿',
    blurb: 'Expand a periodic function as a trigonometric series and compare the partial sum with the original function.',
    methods: [{
      id: 'series',
      label: 'Series expansion',
      endpoint: '/api/fourier/series',
      formula: 'f(x) \\;=\\; \\frac{a_0}{2} + \\sum_{n=1}^{N}\\left[a_n\\cos\\frac{n\\pi x}{L} + b_n\\sin\\frac{n\\pi x}{L}\\right]',
      fields: [
        expr('expression', 'f(x)', 'x', 'Use x as the variable — e.g. x, x^2, abs(x)', true),
        num('half_period', 'Half period L', 3.141592653589793),
        num('terms', 'Number of terms N', 5, { min: 1, max: 50, step: 1 }),
        num('points', 'Plot resolution', 400, { min: 20, max: 2000, step: 10 })
      ],
      render(result) {
        const nodes = [];

        const chart = lineChart({
          x: result.plot.x,
          series: [
            { name: 'Original f(x)', values: result.plot.original, color: token('--series-1') },
            { name: `Fourier sum (N = ${result.terms})`, values: result.plot.approximation, color: token('--series-2') }
          ],
          xLabel: 'x',
          yLabel: 'f(x)'
        });

        nodes.push(card('Approximation', [chart]));

        const accuracy = result.accuracy || {};

        nodes.push(card('Coefficients', [
          stats([
            ['a₀', formatNumber(result.a0)],
            ['Terms', result.terms],
            [`f(${formatNumber(accuracy.at_x, 3)}) exact`, formatNumber(accuracy.exact)],
            ['Partial sum', formatNumber(accuracy.approximation)],
            ['Absolute error', formatNumber(accuracy.absolute_error)]
          ]),
          table(
            [
              { key: 'n', label: 'n' },
              { key: 'an', label: 'aₙ' },
              { key: 'bn', label: 'bₙ' }
            ],
            result.harmonics
          )
        ]));

        return nodes;
      }
    }]
  },

  /* ------------------------------------------------ Calculus */
  {
    id: 'calculus',
    name: 'Calculus',
    glyph: '∫',
    blurb: 'Symbolic differentiation, integration and evaluation.',
    methods: [
      {
        id: 'differentiate',
        label: 'Differentiate',
        endpoint: '/api/calculus/differentiate',
        formula: '\\frac{d}{dx}\\,f(x)',
        fields: [expr('expression', 'f(x)', 'x^2*sin(x)', 'e.g. x^3, exp(x)*cos(x), log(x)', true)]
      },
      {
        id: 'integrate',
        label: 'Integrate',
        endpoint: '/api/calculus/integrate',
        formula: '\\int f(x)\\,dx',
        fields: [expr('expression', 'f(x)', 'x*exp(x)', 'Indefinite integral with respect to x', true)]
      },
      {
        id: 'evaluate',
        label: 'Evaluate',
        endpoint: '/api/calculus/evaluate',
        formula: 'f(x)\\Big|_{x = x_0}',
        fields: [
          expr('expression', 'f(x)', 'x^2 + 1', null, true),
          num('value', 'x₀', 3)
        ]
      }
    ]
  },

  /* ------------------------------------------ Linear algebra */
  {
    id: 'linear-algebra',
    name: 'Linear Algebra',
    glyph: '▦',
    blurb: 'Determinant, inverse, rank and the eigen-decomposition of a square matrix.',
    methods: [{
      id: 'analyze',
      label: 'Analyse a matrix',
      endpoint: '/api/linear-algebra/analyze',
      formula: 'A,\\quad \\det A,\\quad A^{-1},\\quad A\\mathbf{v} = \\lambda\\mathbf{v}',
      fields: [{
        name: 'matrix',
        label: 'Matrix A',
        type: 'textarea',
        value: '2, 1\n1, 2',
        hint: 'One row per line, values separated by commas',
        wide: true
      }],
      render(result) {
        const nodes = [];

        const head = [mathRow('Matrix A', result.matrix)];

        head.push(stats([
          ['Size', `${result.shape.rows} × ${result.shape.cols}`],
          ['Rank', result.rank],
          ['Determinant', isMath(result.determinant) ? result.determinant.text : '—']
        ]));

        nodes.push(card('Matrix', head));

        if (!result.is_square) {
          nodes.push(card('Note', [alert('warn', result.note || 'Not a square matrix.')]));
          return nodes;
        }

        const inverseNodes = result.inverse
          ? [mathRow(null, result.inverse)]
          : [alert('warn', 'No inverse', result.inverse_error)];

        nodes.push(card('Inverse  A⁻¹', inverseNodes));

        const eigenNodes = [];

        if (result.eigenvalues) {
          for (const entry of result.eigenvalues) {
            eigenNodes.push(mathRow(
              `λ  (algebraic multiplicity ${entry.multiplicity})`,
              entry.value
            ));
          }
        } else {
          eigenNodes.push(alert('warn', 'Eigenvalues unavailable', result.eigenvalues_error));
        }

        if (result.eigenvectors) {
          for (const entry of result.eigenvectors) {
            entry.vectors.forEach((vector, index) => {
              eigenNodes.push(mathRow(
                `Eigenvector for λ = ${entry.eigenvalue.text}${entry.vectors.length > 1 ? ` (#${index + 1})` : ''}`,
                vector
              ));
            });
          }
        }

        nodes.push(card('Eigenvalues & eigenvectors', eigenNodes));

        return nodes;
      }
    }]
  },

  /* ----------------------------------------------------- ODE */
  {
    id: 'ode',
    name: 'Differential Equations',
    glyph: 'ƒ',
    blurb: 'Constant-coefficient linear ODEs (CF, PI, complete solution) and the standard first-order methods.',
    methods: [
      {
        id: 'cf',
        label: 'Complementary function',
        endpoint: '/api/ode/complementary-function',
        formula: 'F(D)\\,y = 0',
        fields: [expr('coefficients', 'Operator coefficients', '1, -3, 2',
          'Descending powers of D. D² − 3D + 2 → 1, -3, 2', true)],
        build: (values) => ({ coefficients: splitList(values.coefficients) }),
        render: (result) => card('Result', [
          mathRow('Auxiliary equation', result.auxiliary_equation),
          rootsBlock(result.roots),
          mathRow('Complementary function', result.complementary_function)
        ])
      },
      {
        id: 'pi',
        label: 'Particular integral',
        endpoint: '/api/ode/particular-integral',
        formula: 'y_p \\;=\\; \\frac{1}{F(D)}\\,X',
        fields: [
          expr('coefficients', 'Operator coefficients', '1, -3, 2', 'e.g. 1, -3, 2', true),
          ...forcingFields()
        ],
        build: (values) => ({
          coefficients: splitList(values.coefficients),
          forcing: buildForcing(values)
        })
      },
      {
        id: 'complete',
        label: 'Complete solution',
        endpoint: '/api/ode/complete-solution',
        formula: 'y \\;=\\; y_c + y_p',
        fields: [
          expr('coefficients', 'Operator coefficients', '1, -3, 2', 'e.g. 1, -3, 2', true),
          ...forcingFields()
        ],
        build: (values) => ({
          coefficients: splitList(values.coefficients),
          forcing: buildForcing(values)
        }),
        render(result) {
          const verification = result.verification || {};

          return [
            card('Solution', [
              mathRow('Auxiliary equation', result.auxiliary_equation),
              rootsBlock(result.roots),
              mathRow('Complementary function  y_c', result.complementary_function),
              mathRow('Particular integral  y_p', result.particular_integral),
              mathRow('Complete solution  y', result.complete_solution)
            ]),
            card('Verification', [
              el('div', { style: 'display:flex;flex-wrap:wrap;gap:8px' }, [
                verificationBadge(verification.cf && verification.cf.verified,
                  { good: '✓ CF satisfies F(D)y = 0', warn: '⚠ CF unverified' }),
                verificationBadge(verification.pi && verification.pi.verified,
                  { good: '✓ PI satisfies F(D)y = X', warn: '⚠ PI unverified' }),
                verificationBadge(verification.complete && verification.complete.verified,
                  { good: '✓ Complete solution verified', warn: '⚠ Complete solution unverified' })
              ])
            ])
          ];
        }
      },
      {
        id: 'first-order',
        label: 'First order',
        endpoint: '/api/ode/first-order',
        fields: [
          {
            name: 'method', label: 'Method', type: 'select', value: 'linear', reactive: true,
            options: [
              ['variable_separable', 'Variable separable'],
              ['linear', 'Linear (integrating factor)'],
              ['bernoulli', "Bernoulli's equation"],
              ['exact', 'Exact equation']
            ]
          },
          expr('f_x', 'f(x)', 'x', 'in dy/dx = f(x)·g(y)'),
          expr('g_y', 'g(y)', 'y', 'in dy/dx = f(x)·g(y)'),
          expr('P', 'P(x)', '2/x', 'in dy/dx + P(x)y = Q(x)'),
          expr('Q', 'Q(x)', 'x^2', 'in dy/dx + P(x)y = Q(x)'),
          num('n', 'n', 2, { hint: 'Exponent in Q(x)yⁿ' }),
          expr('M', 'M(x, y)', '2*x*y + y^2', 'in M dx + N dy = 0'),
          expr('N', 'N(x, y)', 'x^2 + 2*x*y', 'in M dx + N dy = 0')
        ],
        visible: {
          variable_separable: ['method', 'f_x', 'g_y'],
          linear: ['method', 'P', 'Q'],
          bernoulli: ['method', 'P', 'Q', 'n'],
          exact: ['method', 'M', 'N']
        },
        formulaFor: {
          variable_separable: '\\frac{dy}{dx} = f(x)\\,g(y)',
          linear: '\\frac{dy}{dx} + P(x)\\,y = Q(x)',
          bernoulli: '\\frac{dy}{dx} + P(x)\\,y = Q(x)\\,y^{n}',
          exact: 'M(x,y)\\,dx + N(x,y)\\,dy = 0'
        }
      }
    ]
  },

  /* ----------------------------------------------------- PDE */
  {
    id: 'pde',
    name: 'Partial Differential Equations',
    glyph: '∂',
    blurb: 'Formation by eliminating arbitrary constants, Lagrange’s linear equation, and the four standard types.',
    methods: [
      {
        id: 'formation',
        label: 'Formation',
        endpoint: '/api/pde/formation',
        formula: 'z = f(x, y;\\,a, b) \\;\\longrightarrow\\; F(x, y, z, p, q) = 0',
        fields: [
          expr('z', 'z = f(x, y)', 'a*x + a^2*y^2 + b', 'Contains the arbitrary constants', true),
          expr('constants', 'Arbitrary constants', 'a, b', 'One or two, comma separated')
        ],
        build: (values) => ({
          z: values.z,
          constants: splitList(values.constants).map(String)
        })
      },
      {
        id: 'lagrange',
        label: "Lagrange's linear PDE",
        endpoint: '/api/pde/lagrange',
        formula: 'Pp + Qq = R,\\qquad \\frac{dx}{P} = \\frac{dy}{Q} = \\frac{dz}{R}',
        fields: [
          expr('P', 'P(x, y, z)', 'y*z'),
          expr('Q', 'Q(x, y, z)', 'x*z'),
          expr('R', 'R(x, y, z)', 'x*y')
        ]
      },
      {
        id: 'standard-type',
        label: 'Standard types',
        endpoint: '/api/pde/standard-type',
        fields: [
          {
            name: 'type', label: 'Type', type: 'select', value: 'clairaut', reactive: true,
            options: [
              ['type_1', 'Type I — f(p, q) = 0'],
              ['clairaut', "Type II — Clairaut's form"],
              ['separable', 'Type III — f(x, p) = g(y, q)'],
              ['no_xy', 'Type IV — f(z, p, q) = 0']
            ]
          },
          expr('f', 'f', 'p*q', 'The function for the chosen type', true),
          expr('g', 'g(y, q)', 'q - y^2', 'Only for the separable type', true)
        ],
        visible: {
          type_1: ['type', 'f'],
          clairaut: ['type', 'f'],
          separable: ['type', 'f', 'g'],
          no_xy: ['type', 'f']
        },
        formulaFor: {
          type_1: 'f(p, q) = 0',
          clairaut: 'z = px + qy + f(p, q)',
          separable: 'f(x, p) = g(y, q)',
          no_xy: 'f(z, p, q) = 0'
        }
      }
    ]
  },

  /* --------------------------------------- Numerical methods */
  {
    id: 'numerical',
    name: 'Numerical Methods',
    glyph: '≈',
    blurb: 'Root finding, finite differences, quadrature, interpolation and linear systems — each cross-checked against an independent method.',
    methods: [
      {
        id: 'root-finding',
        label: 'Root finding',
        endpoint: '/api/numerical/root-finding',
        fields: [
          {
            name: 'method', label: 'Method', type: 'select', value: 'bisection', reactive: true,
            options: [
              ['bisection', 'Bisection'],
              ['newton_raphson', 'Newton–Raphson'],
              ['secant', 'Secant']
            ]
          },
          expr('function', 'f(x)', 'x^3 - x - 2', null, true),
          num('a', 'a', 1), num('b', 'b', 2),
          num('initial_guess', 'Initial guess x₀', 1.5),
          num('x0', 'x₀', 1), num('x1', 'x₁', 2),
          num('tolerance', 'Tolerance', 0.000001)
        ],
        visible: {
          bisection: ['method', 'function', 'a', 'b', 'tolerance'],
          newton_raphson: ['method', 'function', 'initial_guess', 'tolerance'],
          secant: ['method', 'function', 'x0', 'x1', 'tolerance']
        },
        formulaFor: {
          bisection: 'f(a)\\,f(b) < 0 \\;\\Rightarrow\\; c = \\tfrac{a+b}{2}',
          newton_raphson: 'x_{n+1} = x_n - \\frac{f(x_n)}{f\'(x_n)}',
          secant: 'x_{n+1} = x_n - f(x_n)\\,\\frac{x_n - x_{n-1}}{f(x_n) - f(x_{n-1})}'
        }
      },
      {
        id: 'differentiation',
        label: 'Differentiation',
        endpoint: '/api/numerical/differentiation',
        formula: "f'(x_0) \\approx \\frac{f(x_0+h) - f(x_0-h)}{2h}",
        fields: [
          {
            name: 'method', label: 'Formula', type: 'select', value: 'central',
            options: [
              ['forward', 'Forward difference'],
              ['backward', 'Backward difference'],
              ['central', 'Central difference'],
              ['second_central', 'Second derivative (central)']
            ]
          },
          expr('function', 'f(x)', 'x^3 - x - 2', null, true),
          num('x0', 'x₀', 2),
          num('h', 'Step size h', 0.00001)
        ]
      },
      {
        id: 'integration',
        label: 'Integration',
        endpoint: '/api/numerical/integration',
        formula: '\\int_a^b f(x)\\,dx',
        fields: [
          {
            name: 'rule', label: 'Rule', type: 'select', value: 'simpson_1_3',
            reactive: true,
            options: [
              ['trapezoidal', 'Trapezoidal rule'],
              ['simpson_1_3', "Simpson's 1/3 rule (n even)"],
              ['simpson_3_8', "Simpson's 3/8 rule (n multiple of 3)"]
            ]
          },
          expr('function', 'f(x)', 'x^3 - x - 2', null, true),
          num('a', 'Lower limit a', 0),
          num('b', 'Upper limit b', 1),
          num('n', 'Subintervals n', 10, { min: 1, max: 1000, step: 1 })
        ],
        // Each rule constrains n differently, so snap it to a legal
        // default rather than letting the previous rule's value fail.
        adjust(values, changed) {
          if (changed !== 'rule') return values;

          const n = Number(values.n) || 0;

          if (values.rule === 'simpson_3_8') {
            if (n % 3 !== 0) values.n = 9;
          } else if (values.rule === 'simpson_1_3') {
            if (n % 2 !== 0) values.n = 10;
          }

          return values;
        }
      },
      {
        id: 'interpolation',
        label: 'Interpolation',
        endpoint: '/api/numerical/interpolation',
        formula: 'P(x_i) = y_i',
        fields: [
          {
            name: 'method', label: 'Method', type: 'select', value: 'lagrange',
            options: [
              ['lagrange', 'Lagrange'],
              ['newton_divided_difference', "Newton's divided difference"]
            ]
          },
          expr('x_values', 'x values', '0, 1, 2, 3', 'Comma separated', true),
          expr('y_values', 'y values', '1, 2, 9, 28', 'Comma separated', true),
          num('x_eval', 'Evaluate at x', 1.5)
        ]
      },
      {
        id: 'linear-system',
        label: 'Linear systems',
        endpoint: '/api/numerical/linear-system',
        formula: 'A\\mathbf{x} = \\mathbf{b}',
        fields: [
          {
            name: 'method', label: 'Method', type: 'select', value: 'gauss_elimination',
            options: [
              ['gauss_elimination', 'Gauss elimination'],
              ['jacobi', 'Jacobi iteration'],
              ['gauss_seidel', 'Gauss–Seidel iteration']
            ]
          },
          {
            name: 'matrix', label: 'Coefficient matrix A', type: 'textarea',
            value: '4, 1, 2\n3, 5, 1\n1, 1, 3', wide: true,
            hint: 'One row per line'
          },
          expr('vector', 'Right-hand side b', '4, 7, 3', 'Comma separated', true)
        ],
        render(result) {
          const nodes = [card('Solution', [
            el('div', { style: 'display:flex;flex-wrap:wrap;gap:8px' }, [
              verificationBadge(result.verified, {
                good: '✓ Matches numpy.linalg.solve',
                warn: '⚠ Disagrees with the reference solver'
              })
            ]),
            stats(result.solution.map((value, index) => [`x${index + 1}`, formatNumber(value)]))
          ])];

          if (Array.isArray(result.iterations) && result.iterations.length) {
            nodes.push(card('Convergence', [
              table(
                [
                  { key: 'iteration', label: 'Iteration' },
                  { key: 'error', label: 'Max change' },
                  { key: 'x', label: 'x', get: (row) => row.x.map((v) => formatNumber(v, 5)).join(',  ') }
                ],
                result.iterations
              )
            ]));
          }

          return nodes;
        }
      }
    ]
  },

  /* ---------------------------------------------- Transforms */
  {
    id: 'transforms',
    name: 'Transforms',
    glyph: '⇄',
    blurb: 'Laplace, Fourier and Z-transforms with their shifting rules and standard properties.',
    methods: [
      {
        id: 'laplace',
        label: 'Laplace',
        endpoint: '/api/transforms/laplace',
        formula: 'F(s) = \\int_0^{\\infty} f(t)\\,e^{-st}\\,dt',
        fields: [expr('function', 'f(t)', 'sin(t)', 'e.g. sin(t), t^2*exp(-3*t)', true)]
      },
      {
        id: 'laplace-inverse',
        label: 'Inverse Laplace',
        endpoint: '/api/transforms/laplace/inverse',
        formula: 'f(t) = \\mathcal{L}^{-1}\\{F(s)\\}',
        fields: [expr('function', 'F(s)', '1/(s^2+1)', 'e.g. 1/(s^2+4), s/(s^2+9)', true)]
      },
      {
        id: 'laplace-property',
        label: 'Laplace properties',
        endpoint: '/api/transforms/laplace/property',
        fields: [
          {
            name: 'property', label: 'Property', type: 'select', value: 'first_shifting', reactive: true,
            options: [
              ['first_shifting', 'First shifting theorem'],
              ['second_shifting', 'Second shifting theorem'],
              ['derivative', 'Derivative property'],
              ['integral', 'Integral property'],
              ['multiplication_by_t', 'Multiplication by tⁿ'],
              ['division_by_t', 'Division by t']
            ]
          },
          expr('function', 'f(t)', 'sin(t)', null, true),
          num('a', 'a', 3),
          num('order', 'Derivative order', 1, { min: 1, max: 2, step: 1 }),
          num('power', 'n', 2, { min: 1, max: 5, step: 1 })
        ],
        visible: {
          first_shifting: ['property', 'function', 'a'],
          second_shifting: ['property', 'function', 'a'],
          derivative: ['property', 'function', 'order'],
          integral: ['property', 'function'],
          multiplication_by_t: ['property', 'function', 'power'],
          division_by_t: ['property', 'function']
        },
        formulaFor: {
          first_shifting: '\\mathcal{L}\\{e^{at}f(t)\\} = F(s-a)',
          second_shifting: '\\mathcal{L}\\{f(t-a)\\,u(t-a)\\} = e^{-as}F(s)',
          derivative: "\\mathcal{L}\\{f'(t)\\} = sF(s) - f(0)",
          integral: '\\mathcal{L}\\left\\{\\int_0^t f(\\tau)d\\tau\\right\\} = \\frac{F(s)}{s}',
          multiplication_by_t: '\\mathcal{L}\\{t^n f(t)\\} = (-1)^n F^{(n)}(s)',
          division_by_t: '\\mathcal{L}\\left\\{\\frac{f(t)}{t}\\right\\} = \\int_s^{\\infty} F(\\sigma)\\,d\\sigma'
        }
      },
      {
        id: 'fourier',
        label: 'Fourier',
        endpoint: '/api/transforms/fourier',
        // Fourier notation: the same keys mean f(x) and F(ω) here,
        // not the Laplace f(t) and F(s).
        labels: { f: 'f(x)', F: 'F(ω)', direct_transform: 'Computed directly' },

        formula: 'F(w) = \\frac{1}{\\sqrt{2\\pi}}\\int_{-\\infty}^{\\infty} f(x)\\,e^{iwx}\\,dx',
        fields: [
          {
            name: 'kind', label: 'Kind', type: 'select', value: 'sine',
            options: [
              ['complex', 'Complex (infinite) transform'],
              ['sine', 'Fourier sine transform'],
              ['cosine', 'Fourier cosine transform']
            ]
          },
          {
            name: 'direction', label: 'Direction', type: 'select', value: 'forward',
            options: [['forward', 'Forward'], ['inverse', 'Inverse']]
          },
          expr('function', 'f(x)  or  F(w)', 'exp(-2*x)', 'Sine/cosine transforms assume x > 0', true)
        ]
      },
      {
        id: 'fourier-property',
        label: 'Fourier properties',
        endpoint: '/api/transforms/fourier/property',
        // Fourier notation: the same keys mean f(x) and F(ω) here,
        // not the Laplace f(t) and F(s).
        labels: { f: 'f(x)', F: 'F(ω)', direct_transform: 'Computed directly' },

        fields: [
          {
            name: 'property', label: 'Property', type: 'select', value: 'shifting', reactive: true,
            options: [['shifting', 'Shifting'], ['scaling', 'Change of scale']]
          },
          expr('function', 'f(x)', 'exp(-x^2)', null, true),
          num('a', 'a', 2)
        ],
        formulaFor: {
          shifting: '\\mathcal{F}\\{f(x-a)\\} = e^{iwa}F(w)',
          scaling: '\\mathcal{F}\\{f(ax)\\} = \\tfrac{1}{|a|}F\\!\\left(\\tfrac{w}{a}\\right)'
        }
      },
      {
        id: 'z',
        label: 'Z-transform',
        endpoint: '/api/transforms/z',
        formula: 'X(z) = \\sum_{n=0}^{\\infty} x(n)\\,z^{-n}',
        fields: [expr('sequence', 'x(n)', 'a^n', 'e.g. a^n, n*2^n, cos(n*theta)', true)]
      },
      {
        id: 'z-inverse',
        label: 'Inverse Z',
        endpoint: '/api/transforms/z/inverse',
        formula: 'x(n) = \\mathcal{Z}^{-1}\\{X(z)\\}',
        fields: [expr('function', 'X(z)', 'z/((z-1)*(z-2))', 'A rational function of z', true)]
      },
      {
        id: 'z-property',
        label: 'Z properties',
        endpoint: '/api/transforms/z/property',
        fields: [
          {
            name: 'property', label: 'Property', type: 'select', value: 'scaling', reactive: true,
            options: [
              ['linearity', 'Linearity'],
              ['scaling', 'Scaling  aⁿx(n)'],
              ['time_shifting', 'Time shifting'],
              ['initial_value', 'Initial value theorem'],
              ['final_value', 'Final value theorem']
            ]
          },
          expr('sequence', 'x(n)', 'n'),
          expr('sequence_2', 'x₂(n)', 'b**n'),
          expr('function', 'X(z)', 'z/(z-0.5)', 'For the value theorems', true),
          num('a', 'a', 3), num('b', 'b', 2),
          num('k', 'Shift k', 2, { min: 0, max: 20, step: 1 })
        ],
        visible: {
          linearity: ['property', 'sequence', 'sequence_2', 'a', 'b'],
          scaling: ['property', 'sequence', 'a'],
          time_shifting: ['property', 'sequence', 'k'],
          initial_value: ['property', 'function'],
          final_value: ['property', 'function']
        },
        formulaFor: {
          linearity: '\\mathcal{Z}\\{a\\,x_1 + b\\,x_2\\} = aX_1(z) + bX_2(z)',
          scaling: '\\mathcal{Z}\\{a^n x(n)\\} = X\\!\\left(\\tfrac{z}{a}\\right)',
          time_shifting: '\\mathcal{Z}\\{x(n-k)\\} = z^{-k}X(z)',
          initial_value: 'x(0) = \\lim_{z\\to\\infty} X(z)',
          final_value: '\\lim_{n\\to\\infty} x(n) = \\lim_{z\\to 1}(z-1)X(z)'
        }
      }
    ]
  }
];

/* ==========================================================
   Shared builders
   ========================================================== */

function splitList(text) {
  return String(text)
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => (Number.isNaN(Number(part)) ? part : Number(part)));
}

function forcingFields() {
  return [
    {
      name: 'forcing_type', label: 'Forcing function X', type: 'select',
      value: 'exponential', reactive: true,
      options: [
        ['exponential', 'Exponential  e^{ax}'],
        ['sine', 'Sine  sin(ax)'],
        ['cosine', 'Cosine  cos(ax)'],
        ['polynomial', 'Polynomial  X(x)'],
        ['exponential_function', 'Exponential × function  e^{ax}·V(x)']
      ]
    },
    num('forcing_a', 'a', 4),
    expr('forcing_expression', 'X(x) or V(x)', 'x^2', 'Polynomial in x', true)
  ];
}

function buildForcing(values) {
  const type = values.forcing_type;

  const forcing = { type };

  if (type !== 'polynomial') forcing.a = Number(values.forcing_a);
  if (type === 'polynomial' || type === 'exponential_function') {
    forcing.expression = values.forcing_expression;
  }

  return forcing;
}

/** Visible forcing fields depend on the chosen forcing type. */
export function forcingVisibility(type) {
  if (type === 'polynomial') return ['forcing_type', 'forcing_expression'];
  if (type === 'exponential_function') {
    return ['forcing_type', 'forcing_a', 'forcing_expression'];
  }
  return ['forcing_type', 'forcing_a'];
}

function rootsBlock(roots) {
  if (!Array.isArray(roots) || !roots.length) return null;

  return el('div', { class: 'result-row' }, [
    el('div', { class: 'label', text: 'Characteristic roots' }),
    stats(roots.map((entry) => [
      `m (mult. ${entry.multiplicity})`,
      entry.root.text
    ]))
  ]);
}
