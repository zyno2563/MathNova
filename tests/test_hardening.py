"""
Production-hardening guards: timeouts, input limits, CORS, secrets and
error hygiene.

Each test here corresponds to a way the service could be hurt by input
it will actually receive in the wild, rather than to a line of code.
"""

import json
import os
import subprocess
import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def error_of(response):
    return response.json()["error"]


# =========================================================
# Bounded execution
# =========================================================

def test_a_pathological_integral_is_stopped_instead_of_hanging(monkeypatch):
    """
    Cost lives in the mathematics, not in the request size.

    This integrand is 26 characters and passes every length check, but
    runs effectively forever. Before the guard it pinned a worker until
    the platform killed the process.
    """

    from backend.compute import ComputationTimeout, run_guarded

    import sympy as sp

    def pathological():
        return sp.integrate(
            sp.sympify("exp(x**5)*sin(x)**3/log(x)"), sp.Symbol("x")
        )

    started = time.perf_counter()

    with pytest.raises(ComputationTimeout):
        run_guarded(pathological, timeout=2)

    elapsed = time.perf_counter() - started

    assert elapsed < 10, f"took {elapsed:.1f}s to abandon a 2s deadline"


def test_the_deadline_reaches_the_client_as_a_clean_error(monkeypatch):
    monkeypatch.setattr("backend.config.settings.COMPUTE_TIMEOUT", 2)

    response = client.post(
        "/api/calculus/integrate",
        json={"expression": "exp(x**5)*sin(x)**3/log(x)"}
    )

    assert response.status_code == 503

    problem = error_of(response)
    assert problem["code"] == "computation_too_expensive"
    assert "too long" in problem["message"]

    # The service must still be serving.
    assert client.get("/api/health").json()["ok"] is True


def test_a_memory_bomb_is_capped_rather_than_swapping(monkeypatch):
    """
    A deadline alone is not enough.

    An allocation loop drives the host into swap long before a 30s
    deadline expires, degrading every other request in the meantime.
    """

    monkeypatch.setattr("backend.config.settings.COMPUTE_MEMORY_MB", 256)

    from backend.compute import ComputationTooLarge, run_guarded

    def hog():
        blocks = []
        while True:
            blocks.append(bytearray(32 * 1024 * 1024))

    with pytest.raises(ComputationTooLarge):
        run_guarded(hog, timeout=60)


def test_the_memory_cap_is_an_allowance_on_top_of_the_inherited_baseline(
    monkeypatch, tmp_path
):
    """
    Regression: on Render every calculation failed with MemoryError.

    RLIMIT_AS counts every mapping the forked child inherits — the
    interpreter, SymPy, NumPy, OpenBLAS buffers — which on Linux is
    hundreds of megabytes before any work starts. An absolute 256 MB cap
    sat below that baseline. macOS refuses both limits outright, so this
    never showed locally; the ceiling is therefore checked by recording
    what would be set, against a Linux-shaped /proc/self/status.
    """

    import resource

    from backend import compute

    status = tmp_path / "status"
    status.write_text(
        "Name:\tpython\n"
        "VmSize:\t  921600 kB\n"   # 900 MB of inherited address space
        "VmData:\t  307200 kB\n"   # 300 MB of it private data
    )

    real_usage = compute._current_usage
    monkeypatch.setattr(compute, "_current_usage",
                        lambda: real_usage(str(status)))
    monkeypatch.setattr("backend.config.settings.COMPUTE_MEMORY_MB", 256)

    recorded = {}
    monkeypatch.setattr(resource, "getrlimit",
                        lambda c: (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    monkeypatch.setattr(resource, "setrlimit",
                        lambda c, pair: recorded.__setitem__(c, pair[0]))

    compute._apply_child_limits()

    mb = 1024 * 1024

    assert recorded[resource.RLIMIT_AS] == (900 + 256) * mb, (
        "the address-space cap must sit above what the child inherited"
    )
    assert recorded[resource.RLIMIT_DATA] == (300 + 256) * mb


def test_usage_is_read_from_proc_status(tmp_path):
    from backend.compute import _current_usage

    status = tmp_path / "status"
    status.write_text("VmSize:\t 2048 kB\nVmData:\t 1024 kB\nVmRSS:\t 512 kB\n")

    assert _current_usage(str(status)) == {
        "RLIMIT_AS": 2048 * 1024,
        "RLIMIT_DATA": 1024 * 1024,
    }

    # No /proc (macOS, Windows): no baseline, not a crash.
    assert _current_usage(str(tmp_path / "missing")) == {}


def test_a_memory_error_an_engine_wrapped_is_reported_as_memory():
    """
    The engines catch broadly and re-raise as ValueError.

    str(MemoryError()) is empty, so this reached the student as
    "Could not solve dy/dx = Q/P:" under "That input could not be
    solved" — blaming a valid input for the server's own limit.
    """

    from backend.compute import ComputationTooLarge, run_guarded

    def engine_that_wraps():
        try:
            raise MemoryError()
        except Exception as error:
            raise ValueError(f"Could not solve dy/dx = Q/P: {error}")

    with pytest.raises(ComputationTooLarge):
        run_guarded(engine_that_wraps)


def test_the_screenshot_failure_now_reads_as_a_memory_limit():
    """End to end, through the real Lagrange route and its engine."""

    from unittest import mock

    # Patched before the fork, so the child inherits it.
    with mock.patch("sympy.dsolve", side_effect=MemoryError()):
        response = client.post(
            "/api/pde/lagrange", json={"P": "y*z", "Q": "x*z", "R": "x*y"}
        )

    assert response.status_code == 503
    assert error_of(response)["code"] == "computation_too_expensive"
    assert "memory" in error_of(response)["message"]


def test_the_lagrange_example_solves_under_the_guard():
    """The input from the report, with no fault injected."""

    response = client.post(
        "/api/pde/lagrange", json={"P": "y*z", "Q": "x*z", "R": "x*y"}
    )

    assert response.status_code == 200, response.text

    result = response.json()["result"]
    assert result["u"]["text"] == "-x**2 + y**2"
    assert result["v"]["text"] == "-x**2 + z**2"


def test_the_guard_returns_results_and_re_raises_engine_errors():
    """Isolation must be transparent to everything that already worked."""

    from backend.compute import run_guarded

    assert run_guarded(sum, [1, 2, 3]) == 6

    def raises():
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        run_guarded(raises)


def test_exception_types_survive_the_process_boundary():
    """
    `errors.solve()` classifies by exception type.

    If a relayed exception arrived as a bare Exception, a 400 would
    become a 500 and the student would be told the server is broken.
    """

    from backend.compute import run_guarded

    for exception in (ValueError, TypeError, ZeroDivisionError,
                      NotImplementedError):
        def raises(exc=exception):
            raise exc("relayed")

        with pytest.raises(exception):
            run_guarded(raises)


def test_a_result_that_cannot_be_returned_is_a_server_error_not_bad_input():
    """
    A lambdified callable cannot cross a process boundary.

    That is a mistake in the endpoint, so it must be logged as one and
    never reported to the client as invalid input.
    """

    from backend.compute import ResultNotTransferable, run_guarded

    def returns_a_lambda():
        return lambda x: x

    with pytest.raises(ResultNotTransferable):
        run_guarded(returns_a_lambda)


def test_isolation_does_not_slow_ordinary_requests():
    """The guard is only worth having if it is cheap."""

    started = time.perf_counter()

    response = client.post(
        "/api/calculus/differentiate", json={"expression": "x^3*sin(x)"}
    )

    assert response.status_code == 200
    assert time.perf_counter() - started < 3


# =========================================================
# Input limits
# =========================================================

def test_infinity_is_rejected_rather_than_computed_with():
    """
    JSON's parser produces Infinity, and an unbounded float field
    accepted it. The engine then returned a confident-looking answer
    built from a non-number.
    """

    response = client.post(
        "/api/numerical/integration",
        content='{"function":"x^2","a":0,"b":Infinity,"n":10}',
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422, response.text


def test_nan_is_rejected():
    response = client.post(
        "/api/numerical/differentiation",
        content='{"function":"x^2","x0":NaN}',
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422, response.text


def test_every_numeric_field_is_finite_and_bounded():
    """A blanket check, so a new endpoint cannot reintroduce the gap."""

    import importlib
    import inspect

    from pydantic import BaseModel

    unbounded = []

    for name in ("assistant", "calculus", "fourier", "linear_algebra",
                 "numerical", "ode", "pde", "transforms"):
        module = importlib.import_module(f"backend.routers.{name}")

        for class_name, model in vars(module).items():
            if not (inspect.isclass(model) and issubclass(model, BaseModel)
                    and model is not BaseModel
                    and model.__module__ == module.__name__):
                continue

            for field_name, field in model.model_fields.items():
                annotation = str(field.annotation)

                if "Literal" in annotation:
                    continue

                # Only scalars. A collection of numbers is bounded by
                # its length, which the limits above cover separately.
                if "List" in annotation or "list" in annotation:
                    continue

                if "str" in annotation:
                    continue

                if "int" not in annotation and "float" not in annotation:
                    continue

                limits = {
                    attribute
                    for meta in field.metadata
                    for attribute in ("le", "lt")
                    if hasattr(meta, attribute)
                }

                if not limits:
                    unbounded.append(f"{name}.{class_name}.{field_name}")

    assert not unbounded, f"numeric fields with no upper bound: {unbounded}"


def test_an_oversized_body_is_refused_before_it_is_parsed():
    payload = json.dumps({"expression": "x" * 300_000})

    response = client.post(
        "/api/calculus/differentiate",
        content=payload,
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert error_of(response)["code"] == "request_too_large"


def test_interpolation_point_count_is_capped():
    """Interpolation is quadratic; the point count is the real limit."""

    response = client.post("/api/numerical/interpolation", json={
        "method": "lagrange",
        "x_values": [float(index) for index in range(5000)],
        "y_values": [float(index) for index in range(5000)]
    })

    assert response.status_code in (400, 422)


def test_assistant_history_is_capped():
    response = client.post("/api/assistant/chat", json={
        "message": "hi",
        "history": [{"role": "user", "content": "x"}] * 500
    })

    # Rejected on size, never accepted and silently truncated.
    assert response.status_code == 422
    assert error_of(response)["code"] == "validation_error"


def test_a_symbolic_coefficient_cannot_be_unbounded():
    response = client.post("/api/ode/complementary-function", json={
        "coefficients": ["1", "k" * 5000, "2"]
    })

    assert response.status_code == 422


def test_ordinary_requests_still_pass_every_limit():
    """The limits must not have narrowed the real working range."""

    cases = [
        ("/api/transforms/laplace", {"function": "t^2*exp(-3*t)"}),
        ("/api/transforms/laplace/property",
         {"property": "first_shifting", "function": "sin(t)", "a": 3}),
        ("/api/calculus/evaluate", {"expression": "x^2 + sin(x)", "value": 0}),
        ("/api/numerical/root-finding",
         {"method": "bisection", "function": "x^3 - x - 2", "a": 1, "b": 2}),
        ("/api/numerical/integration",
         {"rule": "simpson_1_3", "function": "x^2", "a": 0, "b": 1, "n": 4}),
        ("/api/numerical/interpolation",
         {"method": "lagrange", "x_values": "0, 1, 2, 3",
          "y_values": "1, 2, 9, 28", "x_eval": 1.5}),
        ("/api/linear-algebra/analyze", {"matrix": "2, 1\n1, 2"}),
        ("/api/ode/complementary-function", {"coefficients": [1, -3, 2]}),
        ("/api/pde/formation",
         {"z": "a*x + a^2*y^2 + b", "constants": ["a", "b"]}),
        ("/api/fourier/series", {"expression": "x", "terms": 3}),
    ]

    for path, body in cases:
        response = client.post(path, json=body)
        assert response.status_code == 200, f"{path}: {response.text}"


# =========================================================
# CORS
# =========================================================

def test_no_cors_headers_by_default():
    """
    The bundled frontend is same-origin, so nothing needs CORS.

    An API that echoes an allow-origin header it was never configured
    for is readable by any site a user visits.
    """

    response = client.get(
        "/api/health", headers={"Origin": "https://evil.example"}
    )

    assert "access-control-allow-origin" not in response.headers


def test_a_wildcard_origin_is_refused_outside_debug(monkeypatch):
    from backend.config import Settings

    settings = Settings()
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["*"])
    monkeypatch.setattr(settings, "DEBUG", False)

    assert "*" not in settings.cors_origins


def test_a_wildcard_is_honoured_in_debug(monkeypatch):
    from backend.config import Settings

    settings = Settings()
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["*"])
    monkeypatch.setattr(settings, "DEBUG", True)

    assert settings.cors_origins == ["*"]


def test_localhost_is_trusted_only_in_debug(monkeypatch):
    from backend.config import Settings

    settings = Settings()
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://mathnova.example"])

    monkeypatch.setattr(settings, "DEBUG", False)
    assert settings.cors_origins == ["https://mathnova.example"]

    monkeypatch.setattr(settings, "DEBUG", True)
    assert "http://localhost:8000" in settings.cors_origins


def test_configured_cors_never_allows_credentials():
    """
    Credentialed CORS is what turns a permissive origin into a
    data-exfiltration path. The API is stateless, so it is never needed.
    """

    import inspect

    from backend import main

    source = inspect.getsource(main.create_app)

    assert "allow_credentials=False" in source
    assert "allow_credentials=True" not in source


# =========================================================
# Secrets
# =========================================================

SECRET = "AQ.TESTSECRET_must_never_be_returned_0123456789"


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "gemini")
    return SECRET


def test_no_api_surface_returns_the_key(configured):
    surfaces = [
        client.get("/api/health"),
        client.get("/api/assistant/status"),
        client.get("/api/openapi.json"),
        client.get("/api/docs"),
        client.get("/"),
        client.post("/api/nope", json={}),
        client.post("/api/calculus/differentiate", json={}),
        client.post("/api/calculus/integrate", json={"expression": "))("}),
    ]

    for response in surfaces:
        assert configured not in response.text, (
            f"{response.request.url} leaked the API key"
        )


def test_the_frontend_bundle_contains_no_secret(configured):
    """
    Nothing server-side may be baked into a static asset.

    The frontend reads configuration from /api/assistant/status, which
    reports only a provider name and a model.
    """

    import pathlib

    frontend = pathlib.Path(REPO) / "frontend"

    for path in frontend.rglob("*"):
        if not path.is_file():
            continue

        content = path.read_text(errors="ignore")

        assert configured not in content, f"{path} contains the API key"

        for marker in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "api_key"):
            assert marker not in content, f"{path} references {marker}"

    # And no page may reach an AI provider directly from the browser.
    for path in (frontend / "js").glob("*.js"):
        source = path.read_text()

        assert "googleapis.com" not in source
        assert "generativelanguage" not in source


def test_status_reports_no_credential_or_vendor_fields(configured):
    """
    The status payload is public.

    It carries availability and nothing else — no credential, and no
    provider or model name that would identify the vendor behind the
    deployment.
    """

    payload = client.get("/api/assistant/status").json()["result"]

    assert set(payload) == {"enabled", "message"}


def test_no_api_response_names_the_ai_vendor_or_model(configured):
    """
    Which backend answers is a deployment detail.

    Hiding it only in the interface would be cosmetic: anyone can read
    the API directly, so it is removed at the boundary instead.
    """

    surfaces = [
        client.get("/api/health"),
        client.get("/api/assistant/status"),
        client.get("/api/openapi.json"),
        client.post("/api/assistant/chat", json={"message": ""}),
    ]

    forbidden = ("gemini", "google", "ollama", "anthropic", "claude",
                 "aistudio", "generativelanguage", "free tier")

    for response in surfaces:
        body = response.text.lower()

        for term in forbidden:
            assert term not in body, (
                f"{response.request.url} leaks {term!r}"
            )


def test_an_unavailable_assistant_says_so_without_naming_anything(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    status = client.get("/api/assistant/status").json()["result"]
    chat = client.post("/api/assistant/chat", json={"message": "hi"})

    assert status["enabled"] is False
    assert status["message"]

    for text in (status["message"], chat.json()["error"]["message"]):
        lowered = text.lower()

        for term in ("gemini", "google", "ollama", "aistudio", "api key",
                     "free tier"):
            assert term not in lowered, f"{term!r} leaked in: {text}"


def test_a_message_carrying_a_key_is_redacted(configured):
    """
    A provider can echo the request URL, which carries the key.

    Provider messages are passed through deliberately — one of them
    named the replacement for a retired model — so they are redacted
    rather than suppressed.
    """

    from backend.errors import sanitize

    leaked = f"GET https://api.example.com/v1?key={SECRET} returned 401"

    cleaned = sanitize(leaked)

    assert SECRET not in cleaned
    assert "[redacted]" in cleaned


def test_env_is_ignored_by_git_and_the_example_holds_no_values():
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".env"], cwd=REPO
    ).returncode == 0

    assert ignored, ".env is not gitignored"

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env"],
        cwd=REPO, capture_output=True
    ).returncode == 0

    assert not tracked, ".env is tracked by git"

    assert subprocess.run(
        ["git", "check-ignore", "-q", ".env.example"], cwd=REPO
    ).returncode != 0, ".env.example must stay tracked"

    for line in open(os.path.join(REPO, ".env.example")):
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        name, _, value = line.partition("=")

        assert not value.strip(), (
            f".env.example assigns a value to {name}; it must hold "
            f"placeholders only"
        )


# =========================================================
# Error hygiene
# =========================================================

def test_errors_never_carry_a_stack_trace_or_server_path():
    responses = [
        client.post("/api/calculus/integrate", json={"expression": "))("}),
        client.post("/api/calculus/differentiate", json={}),
        client.post("/api/nope", json={}),
        client.get("/api/assistant/status"),
        client.post("/api/transforms/z", json={"sequence": "@@@"}),
        client.post("/api/linear-algebra/analyze", json={"matrix": "1,2\nx"}),
    ]

    for response in responses:
        body = response.text

        for marker in ("Traceback", "site-packages", 'File "', REPO):
            assert marker not in body, f"{marker!r} leaked in {body[:120]}"


def test_an_unexpected_failure_says_nothing_about_internals(monkeypatch):
    """The catch-all must not describe the fault, even in debug."""

    monkeypatch.setattr("backend.config.settings.DEBUG", True)

    from backend import serialization

    def explode(*args, **kwargs):
        raise RuntimeError("connection string postgres://user:pw@host/db")

    monkeypatch.setattr(serialization, "serialize", explode)

    with TestClient(app, raise_server_exceptions=False) as raw:
        response = raw.post(
            "/api/transforms/laplace", json={"function": "sin(t)"}
        )

    assert response.status_code == 500
    assert "postgres" not in response.text
    assert error_of(response)["message"] == "Unexpected server error."


def test_engine_messages_stay_readable_after_sanitising():
    """Redaction must not damage the mathematics in a message."""

    from backend.errors import sanitize

    for message in (
        "Applying the first shifting theorem: a/(s - 3) is not invertible",
        "Integrating: could not parse '2*x + )'",
        "Create a free API key at https://aistudio.google.com/apikey",
    ):
        assert sanitize(message) == message


def test_a_long_message_is_truncated():
    from backend.errors import MAX_MESSAGE_CHARS, sanitize

    assert len(sanitize("x" * 5000)) <= MAX_MESSAGE_CHARS + 1


def test_every_error_uses_the_one_envelope():
    cases = [
        (client.post("/api/nope", json={}), 404),
        (client.post("/api/calculus/differentiate", json={}), 422),
        (client.post("/api/calculus/integrate", json={"expression": "))("}), 400),
        # A GET on a POST-only path is caught by the /api catch-all,
        # which reports 404 rather than 405. Either is defensible; what
        # matters here is that it uses the same envelope.
        (client.get("/api/transforms/laplace"), 404),
    ]

    for response, expected in cases:
        assert response.status_code == expected, response.text

        payload = response.json()

        assert payload["ok"] is False
        assert set(payload["error"]) == {"code", "message"}
        assert payload["error"]["message"]


# =========================================================
# Response headers
# =========================================================

def test_security_headers_are_present_on_pages_and_errors():
    for response in (client.get("/"),
                     client.get("/api/health"),
                     client.post("/api/nope", json={})):
        for header in ("Content-Security-Policy", "X-Content-Type-Options",
                       "Referrer-Policy", "X-Frame-Options"):
            assert header in response.headers, (
                f"{header} missing from {response.request.url}"
            )

        assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_the_csp_allows_exactly_what_the_page_loads():
    """
    A policy written from a template breaks the page it protects.

    The origins are re-derived from index.html here, so adding a script
    or stylesheet without updating the policy fails the build instead of
    silently blanking KaTeX in production.
    """

    import re

    from backend.security_headers import CONTENT_SECURITY_POLICY

    import glob

    pages = glob.glob(
        os.path.join(REPO, "frontend", "**", "index.html"), recursive=True
    )

    assert pages, "no pages found"

    origins = set()

    for path in pages:
        html = open(path).read()

        origins.update(
            re.match(r"https?://[^/]+", url).group(0)
            for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
        )

    assert origins, "no page loads anything externally; policy may be stale"

    for origin in origins:
        assert origin in CONTENT_SECURITY_POLICY, (
            f"a page loads {origin}, which the CSP does not allow"
        )


def test_the_csp_permits_katex_inline_styles_but_not_inline_scripts():
    """KaTeX writes style attributes; nothing needs inline script."""

    from backend.security_headers import CONTENT_SECURITY_POLICY

    directives = dict(
        (part.split(" ", 1) + [""])[:2]
        for part in CONTENT_SECURITY_POLICY.split("; ")
    )

    assert "'unsafe-inline'" in directives["style-src"]
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in CONTENT_SECURITY_POLICY
    assert directives["frame-ancestors"] == "'none'"


def test_the_page_has_no_inline_script_for_the_policy_to_block():
    """The CSP forbids inline script, so the page must not rely on it."""

    import re

    import glob

    for path in glob.glob(
        os.path.join(REPO, "frontend", "**", "index.html"), recursive=True
    ):
        html = open(path).read()
        route = os.path.relpath(path, os.path.join(REPO, "frontend"))

        assert not re.search(r"<script(?![^>]*\ssrc=)[^>]*>\s*\S", html), (
            f"{route} contains an inline <script>, which the CSP blocks"
        )

        assert not re.search(r'\son(click|load|error|submit)\s*=', html), (
            f"{route} uses an inline event handler, which the CSP blocks"
        )
