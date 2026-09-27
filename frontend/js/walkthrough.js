/**
 * Worked examples and step-by-step explanations, per method.
 *
 * Two jobs, both keyed by `moduleId:methodId`:
 *
 * `examples` — what "Load example" cycles through. The form already
 *   opens on the first one, so a single example made the button look
 *   broken: it recomputed the same thing the Compute button did.
 *
 * `steps` — how a result is read as a worked solution. Each step names
 *   the fields the engine already returns, so the working shown is the
 *   engine's own, never a re-derivation written here. A step whose
 *   fields are absent is skipped, which is what lets one list cover a
 *   method that changes shape with its options.
 */

export const WALKTHROUGH = {

  /* ---------------------------------------- Fourier series */

  'fourier-series:series': {
    examples: [
      { label: 'f(x) = x — the sawtooth', values: { expression: 'x', half_period: 3.141592653589793, terms: 5, points: 400 } },
      { label: 'f(x) = x² — even, cosines only', values: { expression: 'x^2', half_period: 3.141592653589793, terms: 6, points: 400 } },
      { label: 'f(x) = |x| — a corner', values: { expression: 'abs(x)', half_period: 3.141592653589793, terms: 8, points: 400 } }
    ],
    steps: [
      { keys: ['expression', 'half_period'], title: 'Take f(x) over one period',
        explain: 'Every coefficient is an integral across −L to L, so the half period L fixes what "one period" means.' },
      { keys: ['a0'], title: 'Find a₀',
        explain: 'a₀ = (1/L)∫f(x)dx over the period — twice the average height of the curve.' },
      { keys: ['harmonics'], title: 'Find aₙ and bₙ',
        explain: 'aₙ = (1/L)∫f(x)cos(nπx/L)dx and bₙ = (1/L)∫f(x)sin(nπx/L)dx. An even function has no sine terms; an odd one has no cosine terms.' },
      { keys: ['terms'], title: 'Add the harmonics',
        explain: 'The partial sum of N harmonics is plotted against f(x). Near a jump it overshoots however many terms you take.' }
    ]
  },

  /* ---------------------------------------- Calculus */

  'calculus:differentiate': {
    examples: [
      { label: 'x² sin x — product rule', values: { expression: 'x^2*sin(x)' } },
      { label: 'e^x / (x² + 1) — quotient rule', values: { expression: 'exp(x)/(x^2 + 1)' } },
      { label: 'sin(x³) — chain rule', values: { expression: 'sin(x^3)' } }
    ],
    steps: [
      { keys: ['input'], title: 'Read the expression', explain: 'The text is parsed into an exact symbolic expression in x.' },
      { keys: ['derivative'], title: 'Differentiate', explain: 'The product, quotient and chain rules are applied symbolically, not numerically.' },
      { keys: ['simplified'], title: 'Simplify', explain: 'Like terms are collected into the tidiest equivalent form.' }
    ]
  },

  'calculus:integrate': {
    examples: [
      { label: 'x e^x — by parts', values: { expression: 'x*exp(x)' } },
      { label: '1/(x² + 1) — gives arctan', values: { expression: '1/(x^2 + 1)' } },
      { label: 'x·cos(x²) — by substitution', values: { expression: 'x*cos(x^2)' } }
    ],
    steps: [
      { keys: ['input'], title: 'Read the integrand', explain: 'The expression is parsed exactly, so the result stays in closed form.' },
      { keys: ['integral'], title: 'Antidifferentiate', explain: 'Substitution, parts and standard forms are applied until an antiderivative is found.' },
      { keys: ['with_constant'], title: 'Add the constant', explain: 'Antiderivatives differ by a constant, so the general answer carries + C.' }
    ]
  },

  'calculus:evaluate': {
    examples: [
      { label: 'x² + 1 at x = 3', values: { expression: 'x^2 + 1', value: 3 } },
      { label: 'sin x + x² at x = 2 — stays exact', values: { expression: 'x^2 + sin(x)', value: 2 } },
      { label: 'x² + 1 at x = 0.5 — a fraction', values: { expression: 'x^2 + 1', value: 0.5 } }
    ],
    steps: [
      { keys: ['expression', 'at'], title: 'Substitute the value', explain: 'x is replaced by the given number as an exact quantity, not a rounded decimal.' },
      { keys: ['exact'], title: 'Exact value', explain: 'Kept as a fraction or in terms of sin, √ and so on wherever no exact decimal exists.' },
      { keys: ['numeric'], title: 'Decimal value', explain: 'The same quantity evaluated numerically, for when you need a figure.' }
    ]
  },

  /* ---------------------------------------- Linear algebra */

  'linear-algebra:analyze': {
    examples: [
      { label: '[[2,1],[1,2]] — symmetric', values: { matrix: '2, 1\n1, 2' } },
      { label: '[[4,1,2],[3,5,1],[1,1,3]] — 3×3', values: { matrix: '4, 1, 2\n3, 5, 1\n1, 1, 3' } },
      { label: '[[1,2],[2,4]] — singular', values: { matrix: '1, 2\n2, 4' } }
    ],
    steps: [
      { keys: ['matrix', 'shape'], title: 'Read the matrix', explain: 'Rows are split on new lines, entries on commas.' },
      { keys: ['determinant'], title: 'Determinant', explain: 'A determinant of zero means the matrix is singular: no inverse, and its rows are dependent.' },
      { keys: ['rank'], title: 'Rank', explain: 'The number of independent rows — the dimension of what the matrix actually spans.' },
      { keys: ['inverse'], title: 'Inverse', explain: 'Exists only when the determinant is non-zero.' },
      { keys: ['eigenvalues'], title: 'Solve det(A − λI) = 0', explain: 'The roots of the characteristic polynomial are the eigenvalues.' },
      { keys: ['eigenvectors'], title: 'Eigenvectors', explain: 'Each λ gives the directions v with (A − λI)v = 0, which A only stretches.' }
    ]
  },

  /* ---------------------------------------- ODE */

  'ode:cf': {
    examples: [
      { label: 'D² − 3D + 2 — distinct real roots', values: { coefficients: '1, -3, 2' } },
      { label: 'D² − 4D + 4 — a repeated root', values: { coefficients: '1, -4, 4' } },
      { label: 'D² + 4 — a complex pair', values: { coefficients: '1, 0, 4' } }
    ],
    steps: [
      { keys: ['auxiliary_equation'], title: 'Write the auxiliary equation', explain: 'Replace D with m: the operator becomes an ordinary polynomial in m.' },
      { keys: ['roots'], title: 'Find its roots', explain: 'The roots decide the shape of the answer, and repeated roots are counted with their multiplicity.' },
      { keys: ['complementary_function'], title: 'Build the complementary function',
        explain: 'Distinct real roots give e^(mx); a repeated root multiplies by x each time it repeats; a complex pair a ± bi gives e^(ax)(C₁cos bx + C₂sin bx).' }
    ]
  },

  'ode:pi': {
    examples: [
      { label: 'e^(4x) forcing — no resonance', values: { coefficients: '1, -3, 2', forcing_type: 'exponential', forcing_a: 4, forcing_expression: 'x^2' } },
      { label: 'e^(2x) forcing — resonance', values: { coefficients: '1, -3, 2', forcing_type: 'exponential', forcing_a: 2, forcing_expression: 'x^2' } },
      { label: 'sin x forcing', values: { coefficients: '1, 0, 4', forcing_type: 'sine', forcing_a: 1, forcing_expression: 'x^2' } },
      { label: 'Polynomial forcing x²', values: { coefficients: '1, -3, 2', forcing_type: 'polynomial', forcing_a: 4, forcing_expression: 'x^2' } }
    ],
    steps: [
      { keys: ['operator', 'forcing'], title: 'Identify F(D) and the forcing term', explain: 'The particular integral answers the right-hand side only; the complementary function handles the rest.' },
      { keys: ['F_a'], title: 'Evaluate the operator at the forcing', explain: 'For e^(ax) the particular integral is e^(ax)/F(a) — as long as F(a) is not zero.' },
      { keys: ['resonance', 'multiplicity'], title: 'Check for resonance',
        explain: 'If F(a) = 0 the forcing matches a root of the auxiliary equation, the ordinary formula divides by zero, and the answer gains a factor of x for each repetition. This is where hand calculations usually go wrong.' },
      { keys: ['pi'], title: 'Particular integral', explain: 'Substituting it into the original operator reproduces the forcing term exactly.' }
    ]
  },

  'ode:complete': {
    examples: [
      { label: 'D² − 3D + 2 with e^(4x)', values: { coefficients: '1, -3, 2', forcing_type: 'exponential', forcing_a: 4, forcing_expression: 'x^2' } },
      { label: 'D² + 4 with sin x', values: { coefficients: '1, 0, 4', forcing_type: 'sine', forcing_a: 1, forcing_expression: 'x^2' } },
      { label: 'D² − 4D + 4 with x²', values: { coefficients: '1, -4, 4', forcing_type: 'polynomial', forcing_a: 2, forcing_expression: 'x^2' } }
    ],
    steps: [
      { keys: ['auxiliary_equation'], title: 'Write the auxiliary equation', explain: 'Replace D with m to get a polynomial whose roots shape the homogeneous answer.' },
      { keys: ['roots'], title: 'Find its roots', explain: 'Listed with multiplicity, because repetition changes the form of the answer.' },
      { keys: ['complementary_function'], title: 'Complementary function', explain: 'The general solution of the equation with the right-hand side set to zero.' },
      { keys: ['particular_integral'], title: 'Particular integral', explain: 'One solution that does produce the forcing term.' },
      { keys: ['complete_solution'], title: 'Add them together', explain: 'y = complementary function + particular integral. The arbitrary constants stay in the first part.' },
      { keys: ['verification'], title: 'Substitute back', explain: 'The solution is put through the original operator; the residual must come out zero.' }
    ]
  },

  'ode:first-order': {
    examples: [
      { label: 'Linear: dy/dx + (2/x)y = x²', values: { method: 'linear', P: '2/x', Q: 'x^2', f_x: 'x', g_y: 'y', n: 2, M: '2*x*y + y^2', N: 'x^2 + 2*x*y' } },
      { label: 'Separable: dy/dx = x·y', values: { method: 'variable_separable', f_x: 'x', g_y: 'y', P: '2/x', Q: 'x^2', n: 2, M: '2*x*y + y^2', N: 'x^2 + 2*x*y' } },
      { label: 'Bernoulli: dy/dx + (1/x)y = x²y²', values: { method: 'bernoulli', P: '1/x', Q: 'x^2', n: 2, f_x: 'x', g_y: 'y', M: '2*x*y + y^2', N: 'x^2 + 2*x*y' } },
      { label: 'Exact: (2xy + y²)dx + (x² + 2xy)dy = 0', values: { method: 'exact', M: '2*x*y + y^2', N: 'x^2 + 2*x*y', P: '2/x', Q: 'x^2', n: 2, f_x: 'x', g_y: 'y' } }
    ],
    steps: [
      { keys: ['method'], title: 'Choose the method', explain: 'Separate the variables if it separates; use an integrating factor if it is linear; substitute v = y^(1−n) for Bernoulli; check exactness first, since that is the quickest when it applies.' },
      { keys: ['P', 'Q'], title: 'Put it in standard form', explain: 'dy/dx + P(x)y = Q(x) — the form the integrating factor is built from.' },
      { keys: ['M', 'N'], title: 'Identify M and N', explain: 'For M dx + N dy = 0 the equation is exact when ∂M/∂y equals ∂N/∂x.' },
      { keys: ['integrating_factor'], title: 'Find the integrating factor', explain: 'μ = e^(∫P dx). Multiplying through by μ turns the left side into a single derivative.' },
      { keys: ['rhs_integral'], title: 'Integrate', explain: 'Integrating both sides leaves y multiplied by the integrating factor.' },
      { keys: ['solution'], title: 'Solve for y', explain: 'Rearranged into an explicit solution wherever that is possible.' }
    ]
  },

  /* ---------------------------------------- PDE */

  'pde:formation': {
    examples: [
      { label: 'z = ax + a²y² + b', values: { z: 'a*x + a^2*y^2 + b', constants: 'a, b' } },
      { label: 'z = ax + by + ab', values: { z: 'a*x + b*y + a*b', constants: 'a, b' } },
      { label: 'z = a(x + y) — one constant', values: { z: 'a*(x + y)', constants: 'a' } }
    ],
    steps: [
      { keys: ['z'], title: 'Start from the relation', explain: 'The arbitrary constants are what must disappear; the PDE is what is left when they do.' },
      { keys: ['p', 'q'], title: 'Differentiate partially', explain: 'p = ∂z/∂x and q = ∂z/∂y give two more equations involving the same constants.' },
      { keys: ['constants_solved'], title: 'Solve for the constants', explain: 'Each constant is expressed in terms of x, y, z, p and q.' },
      { keys: ['pde'], title: 'Eliminate them', explain: 'Substituting back leaves a relation with no arbitrary constants — the partial differential equation.' }
    ]
  },

  'pde:lagrange': {
    examples: [
      { label: 'yz·p + xz·q = xy', values: { P: 'y*z', Q: 'x*z', R: 'x*y' } },
      { label: 'y²·p + x²·q = z²', values: { P: 'y^2', Q: 'x^2', R: 'z^2' } },
      { label: 'x·p + y·q = z', values: { P: 'x', Q: 'y', R: 'z' } }
    ],
    steps: [
      { keys: ['P', 'Q', 'R'], title: 'Identify P, Q and R', explain: 'Lagrange’s equation is Pp + Qq = R, linear in p and q.' },
      { keys: [], title: 'Form the subsidiary equations', explain: 'dx/P = dy/Q = dz/R. Any two independent integrals of this system solve the whole problem.' },
      { keys: ['u'], title: 'First integral u = c₁', explain: 'Found by pairing two of the ratios and integrating.' },
      { keys: ['v'], title: 'Second integral v = c₂', explain: 'A second independent combination, often needing a different pairing.' },
      { keys: ['general_solution'], title: 'Write the general solution', explain: 'F(u, v) = 0 for an arbitrary function F — the two integrals are all the freedom there is.' }
    ]
  },

  'pde:standard-type': {
    examples: [
      { label: 'Clairaut: z = px + qy + pq', values: { type: 'clairaut', f: 'p*q', g: 'q - y^2' } },
      { label: 'Type 1: f(p, q) = 0', values: { type: 'type_1', f: 'p*q', g: 'q - y^2' } },
      { label: 'Separable: f(x,p) = g(y,q)', values: { type: 'separable', f: 'p*q', g: 'q - y^2' } }
    ],
    steps: [
      { keys: ['type', 'f'], title: 'Recognise the standard type', explain: 'Which variables appear decides the substitution: only p and q, only z with p and q, or a form that separates.' },
      { keys: ['complete_integral'], title: 'Complete integral', explain: 'A solution carrying as many arbitrary constants as there are independent variables.' }
    ]
  },

  /* ---------------------------------------- Numerical methods */

  'numerical:root-finding': {
    examples: [
      { label: 'Bisection on x³ − x − 2', values: { method: 'bisection', function: 'x^3 - x - 2', a: 1, b: 2, initial_guess: 1.5, x0: 1, x1: 2, tolerance: 0.000001 } },
      { label: 'Newton–Raphson on x³ − x − 2', values: { method: 'newton_raphson', function: 'x^3 - x - 2', initial_guess: 1.5, a: 1, b: 2, x0: 1, x1: 2, tolerance: 0.000001 } },
      { label: 'Secant on cos x − x', values: { method: 'secant', function: 'cos(x) - x', x0: 0, x1: 1, a: 0, b: 1, initial_guess: 0.5, tolerance: 0.000001 } }
    ],
    steps: [
      { keys: ['function'], title: 'The equation f(x) = 0', explain: 'A numerical method is for when no formula for the root exists.' },
      { keys: ['method'], title: 'Choose the method',
        explain: 'Bisection always converges if the bracket really changes sign, but slowly. Newton–Raphson is far faster when it works, and diverges from a poor start or a flat derivative. Secant avoids needing the derivative at a small cost in speed.' },
      { keys: ['iterations'], title: 'Iterate', explain: 'Each row narrows the estimate; watch how quickly the change per step shrinks.' },
      { keys: ['root'], title: 'The root', explain: 'Taken once successive estimates agree to within the tolerance.' },
      { keys: ['residual'], title: 'Check it', explain: 'f(root) should be near zero. A large residual means the method converged to nothing useful.' }
    ]
  },

  'numerical:differentiation': {
    examples: [
      { label: 'Central difference, x³ − x − 2 at x = 2', values: { method: 'central', function: 'x^3 - x - 2', x0: 2, h: 0.00001 } },
      { label: 'Forward difference — less accurate', values: { method: 'forward', function: 'x^3 - x - 2', x0: 2, h: 0.00001 } },
      { label: 'Second derivative of sin x at x = 1', values: { method: 'second_central', function: 'sin(x)', x0: 1, h: 0.0001 } }
    ],
    steps: [
      { keys: ['function', 'x0', 'h'], title: 'The function, the point and the step', explain: 'h is the gap between samples: too large loses accuracy, too small loses precision to rounding.' },
      { keys: ['method'], title: 'Choose the formula', explain: 'A central difference cancels the first error term, so it is roughly an order more accurate than forward or backward for the same h.' },
      { keys: ['approximate'], title: 'Finite-difference estimate', explain: 'The derivative estimated from function values alone.' },
      { keys: ['exact'], title: 'Compare with the exact derivative', explain: 'Differentiated symbolically, so you can see the size of the error.' }
    ]
  },

  'numerical:integration': {
    examples: [
      { label: "Simpson's 1/3 on x³ − x − 2", values: { rule: 'simpson_1_3', function: 'x^3 - x - 2', a: 0, b: 1, n: 10 } },
      { label: 'Trapezoidal on the same integral', values: { rule: 'trapezoidal', function: 'x^3 - x - 2', a: 0, b: 1, n: 10 } },
      { label: "Simpson's 3/8 on e^(−x²)", values: { rule: 'simpson_3_8', function: 'exp(-x^2)', a: 0, b: 1, n: 9 } }
    ],
    steps: [
      { keys: ['function', 'a', 'b', 'n'], title: 'The integral and the strips', explain: 'The interval is cut into n strips. Simpson’s 1/3 needs n even; the 3/8 rule needs n a multiple of three.' },
      { keys: ['y_values'], title: 'Sample the integrand', explain: 'The curve is only ever touched at these points — everything else is interpolation.' },
      { keys: ['integral'], title: 'Apply the rule', explain: 'Trapezoids fit straight lines between samples; Simpson fits parabolas, so it is exact up to cubics.' },
      { keys: ['exact_integral'], title: 'Compare with the exact value', explain: 'Integrated symbolically where possible, which shows the truncation error directly.' }
    ]
  },

  'numerical:interpolation': {
    examples: [
      { label: 'Lagrange through (0,1) (1,2) (2,9) (3,28)', values: { method: 'lagrange', x_values: '0, 1, 2, 3', y_values: '1, 2, 9, 28', x_eval: 1.5 } },
      { label: 'Newton divided differences, same data', values: { method: 'newton_divided_difference', x_values: '0, 1, 2, 3', y_values: '1, 2, 9, 28', x_eval: 1.5 } },
      { label: 'Through four points of sin x', values: { method: 'lagrange', x_values: '0, 0.5, 1, 1.5', y_values: '0, 0.4794, 0.8415, 0.9975', x_eval: 0.75 } }
    ],
    steps: [
      { keys: ['points'], title: 'The data', explain: 'n + 1 points determine exactly one polynomial of degree n or less.' },
      { keys: ['method'], title: 'Choose the construction', explain: 'Lagrange and Newton divided differences build the same polynomial by different routes; Newton’s is easier to extend when a point is added.' },
      { keys: ['polynomial'], title: 'The interpolating polynomial', explain: 'It passes through every data point exactly.' },
      { keys: ['y_eval'], title: 'Evaluate it', explain: 'Reliable between the data points; extrapolating outside them is not.' }
    ]
  },

  'numerical:linear-system': {
    examples: [
      { label: 'Gauss elimination, 3×3', values: { method: 'gauss_elimination', matrix: '4, 1, 2\n3, 5, 1\n1, 1, 3', vector: '4, 7, 3' } },
      { label: 'Jacobi iteration, same system', values: { method: 'jacobi', matrix: '4, 1, 2\n3, 5, 1\n1, 1, 3', vector: '4, 7, 3' } },
      { label: 'Gauss–Seidel, same system', values: { method: 'gauss_seidel', matrix: '4, 1, 2\n3, 5, 1\n1, 1, 3', vector: '4, 7, 3' } }
    ],
    steps: [
      { keys: ['A', 'b'], title: 'The system Ax = b', explain: 'The coefficient matrix and the right-hand side.' },
      { keys: ['method'], title: 'Choose the method', explain: 'Elimination is direct and finishes in a fixed number of operations. Jacobi and Gauss–Seidel iterate, and converge when the matrix is diagonally dominant.' },
      { keys: ['upper_triangular_steps'], title: 'Eliminate below the diagonal', explain: 'Row operations clear each column in turn, leaving an upper-triangular system with the same solution.' },
      { keys: ['solution'], title: 'Back-substitute', explain: 'The last equation gives one unknown; working upwards gives the rest.' }
    ]
  },

  /* ---------------------------------------- Transforms */

  'transforms:laplace': {
    examples: [
      { label: 'sin t', values: { function: 'sin(t)' } },
      { label: 't²e^(−3t) — shifted', values: { function: 't^2*exp(-3*t)' } },
      { label: 't·cos(2t)', values: { function: 't*cos(2*t)' } }
    ],
    steps: [
      { keys: ['f'], title: 'The function f(t)', explain: 'Defined for t ≥ 0 — the Laplace transform sees nothing before that.' },
      { keys: ['F'], title: 'Apply the definition', explain: 'F(s) = ∫₀^∞ f(t)e^(−st)dt. In practice standard pairs and the shifting theorems do the work.' }
    ]
  },

  'transforms:laplace-inverse': {
    examples: [
      { label: '1/(s² + 1)', values: { function: '1/(s^2+1)' } },
      { label: '1/(s² + 4)', values: { function: '1/(s^2+4)' } },
      { label: '2/(s + 3)³ — a repeated pole', values: { function: '2/(s+3)^3' } }
    ],
    steps: [
      { keys: ['F'], title: 'The transform F(s)', explain: 'Inverting means finding which f(t) would have produced it.' },
      { keys: ['f'], title: 'Invert it', explain: 'Split into partial fractions, then match each piece to a standard pair. A repeated factor contributes a power of t.' }
    ]
  },

  'transforms:laplace-property': {
    examples: [
      { label: 'First shifting on sin t, a = 3', values: { property: 'first_shifting', function: 'sin(t)', a: 3, order: 1, power: 2 } },
      { label: 'Multiplication by t², on sin t', values: { property: 'multiplication_by_t', function: 'sin(t)', a: 3, order: 1, power: 2 } },
      { label: 'Derivative property on cos t', values: { property: 'derivative', function: 'cos(t)', a: 3, order: 1, power: 2 } }
    ],
    steps: [
      { keys: ['f', 'F'], title: 'Start from the plain transform', explain: 'The property is a shortcut from this known pair to a related one.' },
      { keys: ['shifted_f'], title: 'Apply the property to f(t)', explain: 'The function is modified in the way the theorem describes.' },
      { keys: ['theorem_result'], title: 'What the theorem predicts', explain: 'Obtained by transforming the rule, without integrating again.' },
      { keys: ['direct_transform'], title: 'Transform directly and compare', explain: 'Computed from the definition as an independent check. The two agreeing is what the verification badge reports.' }
    ]
  },

  'transforms:fourier': {
    examples: [
      { label: 'Sine transform of e^(−2x)', values: { kind: 'sine', direction: 'forward', function: 'exp(-2*x)' } },
      { label: 'Complex transform of e^(−x²)', values: { kind: 'complex', direction: 'forward', function: 'exp(-x^2)' } },
      { label: 'Cosine transform of e^(−x)', values: { kind: 'cosine', direction: 'forward', function: 'exp(-x)' } }
    ],
    steps: [
      { keys: ['f'], title: 'The function f(x)', explain: 'Unlike Laplace, the Fourier transform is defined across the whole line.' },
      { keys: ['kind'], title: 'Choose the kind', explain: 'The sine and cosine transforms are the odd and even halves of the full transform, and are the right choice on a half-range.' },
      { keys: ['F', 'Fs', 'Fc'], title: 'Apply the transform', explain: 'Integrating against e^(iwx), sin(wx) or cos(wx) as the kind requires.' }
    ]
  },

  'transforms:fourier-property': {
    examples: [
      { label: 'Shifting on e^(−x²), a = 2', values: { property: 'shifting', function: 'exp(-x^2)', a: 2 } },
      { label: 'Change of scale on e^(−x²), a = 2', values: { property: 'scaling', function: 'exp(-x^2)', a: 2 } },
      { label: 'Shifting on e^(−|x|)', values: { property: 'shifting', function: 'exp(-abs(x))', a: 1 } }
    ],
    steps: [
      { keys: ['f', 'F'], title: 'Start from the plain transform', explain: 'The property relates this pair to a shifted or rescaled one.' },
      { keys: ['shifted_f'], title: 'Apply the property to f(x)', explain: 'Shifting moves the function along x; scaling stretches it.' },
      { keys: ['theorem_result'], title: 'What the theorem predicts', explain: 'A shift multiplies the transform by a phase; a stretch by a compresses it and divides by |a|.' },
      { keys: ['direct_transform'], title: 'Transform directly and compare', explain: 'An independent computation, which is what the verification checks against.' }
    ]
  },

  'transforms:z': {
    examples: [
      { label: 'aⁿ', values: { sequence: 'a^n' } },
      { label: 'n', values: { sequence: 'n' } },
      { label: 'aⁿ·cos(nθ)', values: { sequence: 'a^n*cos(n*b)' } }
    ],
    steps: [
      { keys: ['x_n'], title: 'The sequence x(n)', explain: 'The Z-transform is the discrete counterpart of Laplace: sequences instead of functions.' },
      { keys: ['X'], title: 'Sum the series', explain: 'X(z) = Σ x(n)z^(−n) over n ≥ 0, which is geometric for the standard sequences.' }
    ]
  },

  'transforms:z-inverse': {
    examples: [
      { label: 'z/((z−1)(z−2))', values: { function: 'z/((z-1)*(z-2))' } },
      { label: 'z/(z − 0.5)', values: { function: 'z/(z-0.5)' } },
      { label: 'z/(z − 1)² — a repeated pole', values: { function: 'z/(z-1)^2' } }
    ],
    steps: [
      { keys: ['X'], title: 'The transform X(z)', explain: 'Inverting recovers the sequence it came from.' },
      { keys: ['x_n'], title: 'Invert it', explain: 'Partial fractions in z, then standard pairs. A pole repeated m times contributes a binomial factor in n — the usual place this goes wrong by hand.' }
    ]
  },

  'transforms:z-property': {
    examples: [
      { label: 'Scaling on x(n) = n, a = 3', values: { property: 'scaling', sequence: 'n', sequence_2: 'b**n', function: 'z/(z-0.5)', a: 3, b: 2, k: 2 } },
      { label: 'Time shifting by k = 2', values: { property: 'time_shifting', sequence: 'a^n', sequence_2: 'b**n', function: 'z/(z-0.5)', a: 3, b: 2, k: 2 } },
      { label: 'Final value of z/(z − 0.5)', values: { property: 'final_value', sequence: 'n', sequence_2: 'b**n', function: 'z/(z-0.5)', a: 3, b: 2, k: 2 } }
    ],
    steps: [
      { keys: ['x_n', 'X'], title: 'Start from the plain transform', explain: 'The property maps this pair to a related one without re-summing the series.' },
      { keys: ['scaled_sequence'], title: 'Apply the property to x(n)', explain: 'Scaling multiplies by aⁿ; time shifting delays the sequence by k samples.' },
      { keys: ['theorem_result'], title: 'What the theorem predicts', explain: 'Scaling replaces z by z/a; a delay of k multiplies by z^(−k).' },
      { keys: ['direct_transform'], title: 'Transform directly and compare', explain: 'Computed independently so the two can be checked against each other.' },
      { keys: ['initial_value', 'final_value'], title: 'Value theorems', explain: 'The limits of X(z) as z → ∞ and z → 1 give x(0) and the limit of x(n), without inverting at all.' }
    ]
  }
};

/** The walkthrough for a method, or null. */
export function walkthroughFor(moduleId, methodId) {
  return WALKTHROUGH[`${moduleId}:${methodId}`] || null;
}
