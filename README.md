# MathNova

**Engineering mathematics engine — symbolic, verified, and on the web.**

MathNova solves engineering-mathematics problems and shows the checks
available for each answer: substitution into the original equation,
transform round trips, or comparison against a second method. The
interface reports passed, failed, or unavailable checks alongside the
answer; these checks do not constitute a proof of every returned value.

A FastAPI backend exposes the engines as a REST API; a dependency-free
HTML/CSS/JavaScript frontend consumes it; and an AI assistant can drive
the same engines through tool use.

---

## Modules

| Module | What it does |
|---|---|
| **Fourier Series** | Coefficients `a₀, aₙ, bₙ`, partial-sum reconstruction, error at a sample point |
| **Calculus** | Symbolic differentiation, integration, evaluation |
| **Linear Algebra** | Determinant, rank, inverse, eigenvalues and eigenvectors |
| **ODE** | Complementary function, particular integral (5 forcing types), complete solution; separable / linear / Bernoulli / exact first-order methods |
| **PDE** | Formation by eliminating constants, Lagrange's linear equation, the four standard first-order types |
| **Numerical Methods** | Bisection, Newton–Raphson, secant; finite differences; trapezoidal and Simpson quadrature; Lagrange and Newton interpolation; Gauss elimination, Jacobi, Gauss–Seidel |
| **Transforms** | Laplace and inverse Laplace with six properties; complex / sine / cosine Fourier transforms with shifting and scaling; Z and inverse Z with five properties |
| **AI Assistant** | A provider-agnostic LLM with tool access to every engine above |

---

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn backend.main:app --reload
```

Open <http://127.0.0.1:8000>. Interactive API docs live at
<http://127.0.0.1:8000/api/docs>.

The AI assistant is optional — every mathematics module works without
it. To enable it, get a free [Google AI Studio key](https://aistudio.google.com/apikey)
(no billing account, no credit card):

```bash
cp .env.example .env
# put your key in GEMINI_API_KEY, then restart
```

Prefer to stay offline? Run `ollama serve`, `ollama pull llama3.1`, set
`MATHNOVA_LOCAL_AI_ENABLED=1`, and no key is needed at all.

### Docker

```bash
docker compose up --build          # http://localhost:8000
```

---

## The site

Ten pages, all served as static files by the same app. Navigation is
generated at runtime from one manifest (`frontend/js/pages.js`), so a
page cannot appear in one menu and be missing from another.

| Route | Page |
|---|---|
| `/` | Home |
| `/solver/` | Solver — every engine |
| `/learn/` | Learn — the methods behind the answers |
| `/assistant/` | AI Assistant |
| `/settings/` | Settings — theme, assistant status, stored data |
| `/about/` | About |
| `/contact/` | Contact & Support |
| `/disclaimer/` | AI & Mathematical Disclaimer |
| `/terms/` | Terms & Conditions |
| `/privacy/` | Privacy Policy |

V1 has **no authentication** — no sign-up, no login, no saved history.

**Bug reports and support: <b66475781@gmail.com>.** This is the only
address; the footer carries it on every page, rendered from one constant
so it cannot go stale on a page nobody edits.

---

## Architecture

```
core/        Mathematics engines. Pure SymPy/NumPy, no web imports.
             Unchanged by the web layer — the API calls into them.
backend/     FastAPI.
  routers/     One module per engine; thin request → engine → response.
  assistant/   Provider registry + engine tools.
    providers/   One module per backend behind a common Provider ABC.
    tools.py     Provider-neutral wrappers over the engines.
  serialization.py  One recursive SymPy → {text, latex} converter.
  errors.py    Maps engine exceptions onto a single error envelope.
frontend/    Static HTML/CSS/JS. No build step, no framework.
  js/pages.js    The site map. Every menu is generated from it.
  js/shell.js    Topbar, navigation, footer, assistant — shared by all pages.
  js/modules.js  Declarative form + renderer spec for every module.
  js/chart.js    Hand-rolled SVG chart with crosshair tooltip.
tests/       Engine (79) + API (89) + hardening (34) + pages (38) tests.
legacy/      The superseded Streamlit UI. Not imported, not shipped.
```

Three decisions worth knowing about:

**The mathematics lives in the engines.** The routers validate requests,
enforce resource limits, and serialize results. Shared expression parsing
accepts mathematical syntax without evaluating Python code.

**Results carry both forms.** Every symbolic value crosses the wire as
`{"text": "x**2 + 1", "latex": "x^{2} + 1"}` — the frontend renders the
LaTeX with KaTeX and keeps the text for copying. One recursive
`serialize()` handles SymPy expressions, matrices, NumPy scalars and
arbitrary nesting, so routers never format anything by hand.

**Errors have one shape.** Engines raise ordinary Python exceptions with
messages already written for a student ("f(a) and f(b) must have
opposite signs"). `solve()` catches them and picks a status code, so the
client always receives:

```json
{"ok": false, "error": {"code": "invalid_input", "message": "…"}}
```

---

## API

Every endpoint is `POST` with a JSON body and answers
`{"ok": true, "result": {...}}`.

```bash
curl -X POST http://127.0.0.1:8000/api/transforms/laplace \
     -H 'Content-Type: application/json' \
     -d '{"function": "t^2*exp(-3*t)"}'
```

```json
{
  "ok": true,
  "result": {
    "f": { "text": "t**2*exp(-3*t)", "latex": "t^{2} e^{- 3 t}" },
    "F": { "text": "2/(s + 3)**3",   "latex": "\\frac{2}{\\left(s + 3\\right)^{3}}" },
    "verified": true
  }
}
```

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Status, version, whether the assistant is configured |
| `POST /api/fourier/series` | Fourier series + reconstruction data |
| `POST /api/calculus/{differentiate,integrate,evaluate}` | Symbolic calculus |
| `POST /api/linear-algebra/analyze` | Full matrix analysis |
| `POST /api/ode/{complementary-function,particular-integral,complete-solution,first-order}` | ODEs |
| `POST /api/pde/{formation,lagrange,standard-type}` | PDEs |
| `POST /api/numerical/{root-finding,differentiation,integration,interpolation,linear-system}` | Numerical methods |
| `POST /api/transforms/{laplace,fourier,z}` (+ `/inverse`, `/property`) | Transforms |
| `POST /api/assistant/chat` · `GET /api/assistant/status` | AI assistant |

Full schemas: `/api/docs`.

---

## The AI assistant

The assistant has thirteen tools that call the engines directly —
`compute_laplace_transform`, `solve_homogeneous_ode`, `analyse_matrix`,
`find_root` and so on. It does not do the algebra itself; it calls the
verified engine and explains the result, and the UI shows which tools
ran. That is the whole point of the design: the mathematics comes from
code with tests behind it, not from a language model.

**Which model answers is a configuration detail.** Providers live in
`backend/assistant/providers/`, each one a subclass of a small
`Provider` ABC that takes `(system, messages, tools)` and returns a
`ChatResult`. Two ship today:

| Provider | Requirement | Default model |
|---|---|---|
| `groq` | A free [Groq key](https://console.groq.com/keys) — no card | `openai/gpt-oss-120b`, then two more |
| `gemini` | A free [AI Studio key](https://aistudio.google.com/apikey) — no billing | `gemini-3.6-flash` |
| `local` | Ollama running locally — no key, fully offline | `llama3.1` |

`MATHNOVA_AI_PROVIDER` picks one; the default `auto` tries every provider
that is configured, Groq first, and falls through to the next when one
has reached its free limit or is overloaded. Free tiers are small —
Gemini's allows 20 requests per model per day, and one answer takes about
three — so stacking them is what keeps the assistant answering. An
explicit choice is never silently widened: if you ask for `local` and it
is not running, the error says so rather than quietly using a cloud
provider.

Adding another backend means writing one module and listing it in
`providers/__init__.py`. Nothing above that package changes.

Without any provider configured the endpoint returns a clean `503`, the
panel renders the server's own setup hint, and nothing else in the app
is affected.

---

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/*.mjs    # frontend request, export and print behavior
```

`tests/test_api.py` drives the REST layer against the real engines and
asserts on actual mathematics (that the Fourier coefficients of `f(x)=x`
are `2(-1)ⁿ⁺¹/n`, that the three root finders agree, that a shift of 3
prints as `s - 3` and not `s - 3.0`), plus the error contract and the
serialization layer.

GitHub Actions runs the Python suite on Python 3.12 and the frontend
tests on Node 22 for pushes to `main` and pull requests.

### Render deployment

The existing service uses `render.yaml`: Python 3.12, one web worker,
the free plan, and `/api/health` as its health check. Push tested changes
to the connected `main` branch to trigger deployment when auto-deploy is
enabled. Check the deployment status and verify the public homepage and
solver after the build completes. API keys belong in Render's environment
settings; they must never be committed.

### Traffic, cancellation and startup

The default deployment runs one web worker, admits one calculation or AI
chat at a time, and queues at most two more for up to five seconds. Busy
responses return `503`; request limits return `429`, both with `Retry-After`.
Per visitor, the defaults are 30 math requests and 5 AI requests per minute,
with a global cap of 10 AI requests per minute. Health and static pages
bypass these calculation limits. These limits are in memory, per process,
and reset on restart; multiple replicas need a shared limiter.

Client identity uses the ASGI peer address, not untrusted request headers.
Configure Uvicorn's trusted proxy allowlist for the actual proxy when
needed; otherwise visitors behind the same proxy share a limit.

One 90-second request budget includes queue time and all calculation steps.
Each math step also retains its 30-second cap. Disconnecting or using Cancel
stops the active calculation child once the server receives the disconnect.
AI chats run in a fresh, disposable process so provider calls and tool loops
can also be stopped. Cancellation cannot undo a provider request already
sent, and a buffering reverse proxy may delay disconnect notification.

On repeat visits, the service worker falls back to a cached public page
after two seconds and refreshes it in the background. It never caches API
results, query-string inputs, or Render's temporary startup screen. This
does not eliminate the first-ever visit's hosting startup delay. Solver
requests show a delayed waiting message and a Cancel control.

### Accepted expressions

Inputs support explicit arithmetic (`+`, `-`, `*`, `/`, `^` or `**`),
fractions, ordinary symbol names, standard trigonometric and hyperbolic
functions, `exp`, `log`, `sqrt`, `Abs`, and `Piecewise` with comparisons.
Use `2*x`, for example, instead of `2x`. Arbitrary Python code, object
attributes, indexing, and unlisted function calls are rejected. Expression
size, nesting, and numeric powers are bounded; expensive calculations also
run with time and memory limits.

The homepage includes a live editable matrix example. Solver results
offer copy, LaTeX, text download and print/PDF, with the submitted inputs
shown alongside the answer. Editing an input marks an older result as
outdated. Slow requests time out with a retry message; the homepage demo
also supports cancelling a pending request.

---

## Configuration

All optional. See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Enables the assistant (free tier) |
| `MATHNOVA_AI_PROVIDER` | `auto` | `auto`, `gemini` or `local` |
| `MATHNOVA_AI_MODEL` | `gemini-3.6-flash` | Cloud model |
| `MATHNOVA_LOCAL_AI_ENABLED` | `0` | Offline Ollama fallback |
| `MATHNOVA_LOCAL_AI_URL` | `localhost:11434` | Ollama server |
| `MATHNOVA_LOCAL_AI_MODEL` | `llama3.1` | Local model |
| `MATHNOVA_ASSISTANT_MAX_TOKENS` | `16000` | Reply ceiling |
| `MATHNOVA_ASSISTANT_MAX_TOOL_TURNS` | `8` | Bounds the agentic loop |
| `MATHNOVA_COMPUTE_TIMEOUT` | `30` | Per-calculation deadline, seconds |
| `MATHNOVA_COMPUTE_MEMORY_MB` | `1024` | Memory a calculation may use beyond the worker's own |
| `MATHNOVA_MAX_REQUEST_BYTES` | `131072` | Largest accepted request body |
| `MATHNOVA_ASSISTANT_TIMEOUT` | `45` | Provider request timeout, seconds |
| `MATHNOVA_CORS_ORIGINS` | same-origin | Comma-separated extra origins |
| `MATHNOVA_DEBUG` | `0` | Verbose logging |
| `PORT` / `WEB_CONCURRENCY` | `8000` / `2` | Server binding |

---

## Running it safely

Symbolic mathematics has no useful upper bound on cost, and the
expensive inputs are not the large ones: `exp(x**5)*sin(x)**3/log(x)` is
26 characters and integrates forever. So every engine call runs in a
forked child process under a wall-clock deadline and an address-space
cap (`backend/compute.py`). If it overruns, the child is killed and the
request returns `503 computation_too_expensive`; the worker serving the
request was never the process doing the work, so it cannot be hung or
OOM-killed by one bad expression. Fork costs about a millisecond, which
is nothing next to the engines themselves.

Alongside that:

* **Input limits** — every numeric field is finite and bounded, so
  `Infinity` and `NaN` cannot reach an engine; collections have
  ceilings; request bodies over 128 KB are refused before being read.
* **CORS** — off by default, because the frontend is served by this same
  app and is therefore same-origin. Credentials are never allowed, and
  a `*` origin is refused outside debug mode.
* **Secrets** — server-side only. No API key appears in any response,
  any static asset, or the OpenAPI schema, and outgoing error messages
  are redacted before they are sent.
* **Errors** — one envelope everywhere, with no stack trace, no
  filesystem path and no internal detail, in debug mode as well.
* **Response headers** — a CSP written against what the page actually
  loads, plus `nosniff`, `Referrer-Policy` and frame denial.

---

## Deploying

`Dockerfile` (non-root, healthcheck), `docker-compose.yml`, `Procfile`
and `render.yaml` are included. The app is a single stateless process
serving both the API and the static frontend, so any container or
Python host works.

**Sizing note.** Symbolic integration is CPU-bound and occasionally
slow; a hard per-request compute timeout is *not* implemented. Inputs
are bounded instead (expression length, `N ≤ 50`, matrices `≤ 8×8`,
`≤ 25` interpolation points). Run more workers rather than more threads,
and put a request timeout in front of it in production.
