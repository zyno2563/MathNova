"""
API-level tests for the MathNova web backend.

These exercise the REST layer end to end against the real engines —
the maths itself is covered by the per-engine test modules.
"""

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def ok(path, body):
    """POST and assert the success envelope, returning the result."""

    response = client.post(path, json=body)

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["ok"] is True, payload

    return payload["result"]


def failure(path, body):
    """POST and assert the error envelope, returning the error object."""

    response = client.post(path, json=body)

    assert response.status_code >= 400
    payload = response.json()

    assert payload["ok"] is False
    assert "code" in payload["error"]
    assert payload["error"]["message"]

    return payload["error"]


# =========================================================
# META
# =========================================================

def test_health():
    payload = client.get("/api/health").json()

    assert payload["ok"] is True
    assert payload["result"]["status"] == "healthy"
    assert "transforms" in payload["result"]["modules"]


def test_frontend_is_served():
    response = client.get("/")

    assert response.status_code == 200
    assert "MathNova" in response.text


def test_unknown_api_route_uses_the_error_envelope():
    response = client.post("/api/does-not-exist", json={})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# =========================================================
# FOURIER SERIES
# =========================================================

def test_fourier_series_of_x_has_known_coefficients():
    result = ok("/api/fourier/series", {
        "expression": "x",
        "half_period": 3.141592653589793,
        "terms": 4,
        "points": 50
    })

    # f(x) = x on (-L, L) is odd: every a_n vanishes and b_n = 2(-1)^(n+1)/n.
    assert abs(result["a0"]) < 1e-6
    assert all(abs(value) < 1e-6 for value in result["an"])

    for index, b_n in enumerate(result["bn"], start=1):
        expected = 2 * (-1) ** (index + 1) / index
        assert b_n == pytest.approx(expected, abs=1e-6)

    assert len(result["plot"]["x"]) == 50
    assert len(result["plot"]["approximation"]) == 50


def test_fourier_series_rejects_an_unparseable_function():
    failure("/api/fourier/series", {"expression": "x^^^2"})


# =========================================================
# CALCULUS
# =========================================================

def test_differentiate():
    result = ok("/api/calculus/differentiate", {"expression": "x^2*sin(x)"})

    assert result["derivative"]["text"] == "x**2*cos(x) + 2*x*sin(x)"
    assert "latex" in result["derivative"]


def test_integrate():
    result = ok("/api/calculus/integrate", {"expression": "x*exp(x)"})

    assert result["integral"]["text"] == "(x - 1)*exp(x)"


def test_evaluate():
    result = ok("/api/calculus/evaluate", {"expression": "x^2 + 1", "value": 3})

    assert result["numeric"] == pytest.approx(10.0)


def test_the_exact_value_is_exact_not_a_float():
    """
    A field labelled "Exact value" must not hold a 15-digit float.

    JSON has no integer type that survives a float field, so x = 3
    arrived as 3.0 and SymPy returned 10.0000000000000. The transforms
    router already avoided this with Rational(str(x)); evaluate did not.
    """

    result = ok("/api/calculus/evaluate", {"expression": "x^2 + 1", "value": 3})

    assert result["exact"]["text"] == "10"
    assert result["exact"]["latex"] == "10"


def test_an_exact_value_stays_in_closed_form():
    """A non-integer point must not collapse the answer to decimals."""

    half = ok("/api/calculus/evaluate", {"expression": "x^2 + 1", "value": 0.5})

    assert half["exact"]["text"] == "5/4"
    assert half["numeric"] == pytest.approx(1.25)

    symbolic = ok(
        "/api/calculus/evaluate", {"expression": "x^2 + sin(x)", "value": 2}
    )

    assert "sin(2)" in symbolic["exact"]["text"]


def test_calculus_rejects_bad_syntax():
    error = failure("/api/calculus/differentiate", {"expression": "x^^2 +"})

    assert error["code"] == "invalid_input"


# =========================================================
# LINEAR ALGEBRA
# =========================================================

def test_matrix_analysis_from_text():
    result = ok("/api/linear-algebra/analyze", {"matrix": "2, 1\n1, 2"})

    assert result["determinant"]["text"] == "3"
    assert result["rank"] == 2
    assert result["is_square"] is True

    eigenvalues = {entry["value"]["text"] for entry in result["eigenvalues"]}
    assert eigenvalues == {"1", "3"}


def test_matrix_analysis_from_rows():
    result = ok("/api/linear-algebra/analyze", {"rows": [[4, 1], [2, 3]]})

    assert result["determinant"]["text"] == "10"


def test_singular_matrix_reports_no_inverse_without_failing():
    result = ok("/api/linear-algebra/analyze", {"rows": [[1, 2], [2, 4]]})

    assert result["determinant"]["text"] == "0"
    assert result["inverse"] is None
    assert result["inverse_error"]


def test_non_square_matrix_is_reported_not_rejected():
    result = ok("/api/linear-algebra/analyze", {"rows": [[1, 2, 3], [4, 5, 6]]})

    assert result["is_square"] is False
    assert result["note"]


def test_oversized_matrix_is_rejected():
    rows = [[1] * 9 for _ in range(9)]
    failure("/api/linear-algebra/analyze", {"rows": rows})


# =========================================================
# ODE
# =========================================================

def test_complementary_function():
    result = ok("/api/ode/complementary-function", {"coefficients": [1, -3, 2]})

    assert result["auxiliary_equation"]["text"] == "m**2 - 3*m + 2"
    assert {entry["root"]["text"] for entry in result["roots"]} == {"1", "2"}


def test_complete_solution_is_verified():
    result = ok("/api/ode/complete-solution", {
        "coefficients": [1, -3, 2],
        "forcing": {"type": "polynomial", "expression": "x^2"}
    })

    assert result["verification"]["all_verified"] is True
    assert "complete_solution" in result


@pytest.mark.parametrize("forcing", [
    {"type": "exponential", "a": 4},
    {"type": "sine", "a": 2},
    {"type": "cosine", "a": 2},
    {"type": "polynomial", "expression": "x^2"},
    {"type": "exponential_function", "a": 4, "expression": "x^2"},
])
def test_every_forcing_type_produces_a_particular_integral(forcing):
    result = ok("/api/ode/particular-integral", {
        "coefficients": [1, -3, 2],
        "forcing": forcing
    })

    assert "pi" in result


def test_forcing_requires_its_parameter():
    failure("/api/ode/complete-solution", {
        "coefficients": [1, -3, 2],
        "forcing": {"type": "exponential"}
    })


@pytest.mark.parametrize("body", [
    {"method": "variable_separable", "f_x": "x", "g_y": "y"},
    {"method": "linear", "P": "2/x", "Q": "x^2"},
    {"method": "bernoulli", "P": "1/x", "Q": "x^2", "n": 2},
    {"method": "exact", "M": "2*x*y + y^2", "N": "x^2 + 2*x*y"},
])
def test_first_order_methods_are_verified(body):
    result = ok("/api/ode/first-order", body)

    assert result["verified"] is True


def test_non_exact_equation_is_rejected_clearly():
    error = failure("/api/ode/first-order", {
        "method": "exact", "M": "y", "N": "x^2"
    })

    assert "exact" in error["message"].lower()


# =========================================================
# PDE
# =========================================================

def test_pde_formation():
    result = ok("/api/pde/formation", {
        "z": "a*x + a^2*y^2 + b",
        "constants": ["a", "b"]
    })

    assert result["verified"] is True


def test_lagrange_invariants_are_verified():
    result = ok("/api/pde/lagrange", {"P": "y*z", "Q": "x*z", "R": "x*y"})

    assert result["verified"] is True
    assert result["u"]["text"]
    assert result["v"]["text"]


@pytest.mark.parametrize("body", [
    {"type": "type_1", "f": "p*q - 1"},
    {"type": "clairaut", "f": "p*q"},
    {"type": "separable", "f": "p^2 - x", "g": "q - y^2"},
    {"type": "no_xy", "f": "p*q - z"},
])
def test_standard_pde_types_are_verified(body):
    result = ok("/api/pde/standard-type", body)

    assert result["verified"] is True


# =========================================================
# NUMERICAL
# =========================================================

@pytest.mark.parametrize("body", [
    {"method": "bisection", "function": "x^3 - x - 2", "a": 1, "b": 2},
    {"method": "newton_raphson", "function": "x^3 - x - 2", "initial_guess": 1.5},
    {"method": "secant", "function": "x^3 - x - 2", "x0": 1, "x1": 2},
])
def test_root_finders_agree_on_the_same_root(body):
    result = ok("/api/numerical/root-finding", body)

    assert result["root"] == pytest.approx(1.5213797, abs=1e-4)
    assert result["verified"] is True
    assert result["iterations"]


def test_bisection_requires_a_sign_change():
    error = failure("/api/numerical/root-finding", {
        "method": "bisection", "function": "x^2 + 1", "a": 0, "b": 1
    })

    assert "opposite signs" in error["message"]


def test_numerical_differentiation_matches_the_exact_derivative():
    result = ok("/api/numerical/differentiation", {
        "method": "central", "function": "x^3 - x - 2", "x0": 2
    })

    assert result["approximate"] == pytest.approx(11.0, abs=1e-3)
    assert result["exact"] == pytest.approx(11.0)
    assert result["verified"] is True


def test_simpson_matches_the_exact_integral():
    result = ok("/api/numerical/integration", {
        "rule": "simpson_1_3", "function": "x^3 - x - 2", "a": 0, "b": 1, "n": 10
    })

    assert result["integral"] == pytest.approx(-2.25, abs=1e-9)


def test_simpson_three_eighth_requires_a_multiple_of_three():
    failure("/api/numerical/integration", {
        "rule": "simpson_3_8", "function": "x^2", "a": 0, "b": 1, "n": 10
    })


@pytest.mark.parametrize("method", ["lagrange", "newton_divided_difference"])
def test_interpolation_recovers_the_underlying_cubic(method):
    result = ok("/api/numerical/interpolation", {
        "method": method,
        "x_values": "0, 1, 2, 3",
        "y_values": "1, 2, 9, 28",
        "x_eval": 1.5
    })

    assert result["polynomial"]["text"] == "x**3 + 1"
    assert result["y_eval"] == pytest.approx(4.375)
    assert result["verified"] is True


def test_interpolation_rejects_mismatched_lengths():
    failure("/api/numerical/interpolation", {
        "x_values": "1, 2, 3", "y_values": "1, 2"
    })


@pytest.mark.parametrize("method", ["gauss_elimination", "jacobi", "gauss_seidel"])
def test_linear_solvers_agree(method):
    result = ok("/api/numerical/linear-system", {
        "method": method,
        "matrix": "4, 1, 2\n3, 5, 1\n1, 1, 3",
        "vector": "4, 7, 3"
    })

    assert result["verified"] is True

    for value, expected in zip(result["solution"], [0.5, 1.0, 0.5]):
        assert value == pytest.approx(expected, abs=1e-5)


def test_singular_system_is_rejected():
    failure("/api/numerical/linear-system", {
        "method": "gauss_elimination", "matrix": "1,2\n2,4", "vector": "3,6"
    })


# =========================================================
# TRANSFORMS
# =========================================================

def test_laplace_transform_round_trips():
    forward = ok("/api/transforms/laplace", {"function": "sin(t)"})

    assert forward["F"]["text"] == "1/(s**2 + 1)"
    assert forward["verified"] is True

    inverse = ok("/api/transforms/laplace/inverse", {"function": "1/(s^2+1)"})

    assert inverse["f"]["text"] == "sin(t)"


def test_first_shifting_theorem_keeps_the_shift_exact():
    result = ok("/api/transforms/laplace/property", {
        "property": "first_shifting", "function": "sin(t)", "a": 3
    })

    # A JSON 3 must not surface as (s - 3.0).
    assert result["theorem_result"]["text"] == "1/((s - 3)**2 + 1)"
    assert result["verified"] is True


@pytest.mark.parametrize("prop,extra", [
    ("first_shifting", {"a": 3}),
    ("second_shifting", {"a": 2}),
    ("derivative", {"order": 2}),
    ("integral", {}),
    ("multiplication_by_t", {"power": 2}),
    ("division_by_t", {}),
])
def test_laplace_properties_are_verified(prop, extra):
    function = "exp(-2*t)" if prop == "multiplication_by_t" else "sin(t)"

    if prop == "second_shifting":
        function = "t^2"

    result = ok("/api/transforms/laplace/property", {
        "property": prop, "function": function, **extra
    })

    assert result["verified"] is True


@pytest.mark.parametrize("kind,function", [
    ("sine", "exp(-2*x)"),
    ("cosine", "exp(-2*x)"),
    ("complex", "exp(-x^2)"),
])
def test_fourier_transforms_are_verified(kind, function):
    result = ok("/api/transforms/fourier", {
        "kind": kind, "direction": "forward", "function": function
    })

    assert result["verified"] is True


def test_z_transform_of_cosine_sequence():
    result = ok("/api/transforms/z", {"sequence": "cos(n*theta)"})

    assert result["X"]["text"] == "z*(z - cos(theta))/(z**2 - 2*z*cos(theta) + 1)"
    assert result["verified"] is True


def test_inverse_z_transform():
    result = ok("/api/transforms/z/inverse", {"function": "z/((z-1)*(z-2))"})

    assert result["x_n"]["text"] == "2**n - 1"
    assert result["verified"] is True


@pytest.mark.parametrize("body", [
    {"property": "linearity", "sequence": "a**n", "sequence_2": "b**n", "a": 2, "b": 3},
    {"property": "scaling", "sequence": "n", "a": 3},
    {"property": "time_shifting", "sequence": "a**n", "k": 2},
    {"property": "initial_value", "function": "z/(z-2)"},
    {"property": "final_value", "function": "z/(z-0.5)"},
])
def test_z_properties_are_verified(body):
    result = ok("/api/transforms/z/property", body)

    assert result["verified"] is True


def test_z_property_requires_its_inputs():
    failure("/api/transforms/z/property", {"property": "scaling", "sequence": "n"})


# =========================================================
# ASSISTANT — provider-agnostic
# =========================================================

def test_assistant_status_reports_availability_and_nothing_else():
    """
    The status endpoint says whether the assistant can answer.

    It used to name the provider, its pricing tier and the model. That
    identifies a vendor and a deployment to anyone who requests the
    URL, so it is reported to the log instead.
    """

    payload = client.get("/api/assistant/status").json()

    assert payload["ok"] is True

    result = payload["result"]

    assert set(result) == {"enabled", "message"}
    assert isinstance(result["enabled"], bool)

    if not result["enabled"]:
        assert result["message"], "an unavailable assistant must say so"


def test_assistant_without_any_provider_fails_cleanly(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")

    response = client.post("/api/assistant/chat", json={"message": "hello"})

    assert response.status_code == 503

    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "assistant_unavailable"

    message = payload["error"]["message"]

    # Generic on purpose: the provider's own message quotes its setup
    # instructions and names the vendor.
    assert "unavailable" in message.lower()
    assert "aistudio" not in message.lower()


def test_assistant_rejects_an_empty_message():
    response = client.post("/api/assistant/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_selecting_an_unknown_provider_is_reported_to_the_operator(monkeypatch):
    """
    The operator needs the detail; the visitor must not get it.

    Naming the configured backend in an HTTP response would tell anyone
    who asks which vendor this deployment uses.
    """

    from backend.assistant import providers

    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "not-a-provider")

    with pytest.raises(providers.NotConfigured, match="not-a-provider"):
        providers.resolve()

    response = client.post("/api/assistant/chat", json={"message": "hi"})

    assert response.status_code == 503
    assert "not-a-provider" not in response.json()["error"]["message"]


def test_explicit_provider_choice_is_not_silently_replaced(monkeypatch):
    """Choosing `local` must not quietly fall back to the cloud one."""

    from backend.assistant import providers

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "local")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    with pytest.raises(providers.NotConfigured) as raised:
        providers.resolve()

    # The operator is told exactly what is wrong.
    assert "local" in str(raised.value)
    assert "ollama" in str(raised.value).lower()

    # The visitor is not.
    assert client.post(
        "/api/assistant/chat", json={"message": "hi"}
    ).status_code == 503


# ---------------------------------------------------------
# Tool layer (provider-independent)
# ---------------------------------------------------------

def test_tools_expose_valid_json_schema():
    from backend.assistant.tools import TOOLS

    assert len(TOOLS) >= 10

    for tool in TOOLS:
        schema = tool.to_json_schema()

        assert schema["name"] and schema["description"]
        assert schema["parameters"]["type"] == "object"
        assert isinstance(schema["parameters"]["properties"], dict)

        for name, prop in schema["parameters"]["properties"].items():
            assert prop["type"] in (
                "string", "integer", "number", "boolean"
            ), f"{tool.name}.{name} has a non-JSON type"


def test_tools_call_the_verified_engines():
    from backend.assistant.tools import TOOLS_BY_NAME

    answer = TOOLS_BY_NAME["compute_laplace_transform"].run(
        {"function": "t^2*exp(-3*t)"}
    )

    assert "2/(s + 3)**3" in answer
    assert "verified" in answer


def test_tools_report_failures_as_text_never_raising():
    from backend.assistant.tools import TOOLS_BY_NAME

    answer = TOOLS_BY_NAME["differentiate_expression"].run({"expression": "x^^^"})

    assert isinstance(answer, str)
    assert "failed" in answer.lower()


def test_tools_tolerate_improvised_arguments():
    """Models sometimes add keys or omit optional ones."""

    from backend.assistant.tools import TOOLS_BY_NAME

    answer = TOOLS_BY_NAME["compute_fourier_transform"].run(
        {"function": "exp(-2*x)", "nonsense": 1}
    )

    assert "Fs(w)" in answer


def test_unknown_tool_name_is_reported_not_raised():
    from backend.assistant.providers.base import run_tool
    from backend.assistant.tools import TOOLS_BY_NAME

    assert "No such tool" in run_tool(TOOLS_BY_NAME, "nope", {})


# ---------------------------------------------------------
# Gemini wire shape — exercised against a stub endpoint, so no
# API key, no network and no quota are needed.
# ---------------------------------------------------------

def _stub_gemini(turns):
    """
    Serve canned generateContent responses and record every request.

    `turns` is a list of `parts` lists; the last repeats once exhausted.
    """

    import json
    import socketserver
    import threading
    from http.server import BaseHTTPRequestHandler

    recorded = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            recorded.append({
                "path": self.path,
                "body": json.loads(self.rfile.read(length)),
            })

            parts = turns[min(len(recorded) - 1, len(turns) - 1)]

            payload = json.dumps({
                "candidates": [{
                    "content": {"role": "model", "parts": parts},
                    "finishReason": "STOP",
                }]
            }).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    return server, recorded


def _gemini_provider(server):
    from backend.assistant.providers.gemini import GeminiProvider

    from backend.assistant.providers.gemini import DEFAULT_MODEL

    return GeminiProvider(
        model=DEFAULT_MODEL,
        base_url=f"http://127.0.0.1:{server.server_address[1]}",
    )


def test_gemini_request_carries_tools_and_system_prompt(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from backend.assistant.service import SYSTEM_PROMPT
    from backend.assistant.tools import TOOLS

    server, recorded = _stub_gemini([[{"text": "F(s) = 1/s**2"}]])

    try:
        provider = _gemini_provider(server)
        result = provider.chat(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "Laplace of t"}],
            tools=TOOLS,
            max_tool_turns=8,
            max_output_tokens=16000,
        )
    finally:
        server.shutdown()

    assert result.reply == "F(s) = 1/s**2"
    assert result.provider == "gemini"
    from backend.assistant.providers.gemini import DEFAULT_MODEL

    assert result.model == DEFAULT_MODEL
    assert result.truncated is False

    body = recorded[0]["body"]

    # Every engine tool must reach the model.
    declarations = body["tools"][0]["functionDeclarations"]
    assert len(declarations) == len(TOOLS)
    assert {d["name"] for d in declarations} == {t.name for t in TOOLS}

    # Automatic function calling must stay off so the loop is ours.
    assert body["systemInstruction"]["parts"][0]["text"].startswith(
        "You are the MathNova Mathematics Assistant"
    )
    assert body["generationConfig"]["maxOutputTokens"] == 16000


def test_gemini_executes_tool_calls_against_the_engines(monkeypatch):
    """A function call must run the real engine and feed the result back."""

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from backend.assistant.tools import TOOLS

    server, recorded = _stub_gemini([
        [{"functionCall": {"name": "compute_laplace_transform",
                           "args": {"function": "t^2*exp(-3*t)"}}}],
        [{"text": "The transform is 2/(s+3)^3."}],
    ])

    try:
        provider = _gemini_provider(server)
        result = provider.chat(
            system="test",
            messages=[{"role": "user", "content": "Laplace of t^2 e^-3t"}],
            tools=TOOLS,
            max_tool_turns=8,
        )
    finally:
        server.shutdown()

    assert result.tools_used == ["compute_laplace_transform"]
    assert "2/(s+3)^3" in result.reply

    # The second request must carry the engine's real answer back.
    followup = recorded[1]["body"]
    sent = json.dumps(followup)

    assert "functionResponse" in sent
    assert "2/(s + 3)**3" in sent, "the engine result never reached the model"


def test_a_retired_model_error_keeps_googles_replacement_advice():
    """
    Google retires models for new keys while still listing them.

    Its 404 body names the model to switch to. Swallowing that behind a
    generic line cost a debugging round-trip, so the message is passed
    through.
    """

    from backend.assistant.providers.gemini import GeminiProvider

    raw = (
        "404 NOT_FOUND. {'error': {'code': 404, 'message': 'This model "
        "models/gemini-2.5-flash is no longer available to new users. "
        "Please update your code to use models/gemini-3.6-flash.', "
        "'status': 'NOT_FOUND'}}"
    )

    translated = GeminiProvider(model="gemini-2.5-flash")._translate(
        RuntimeError(raw)
    )

    assert translated.code == "assistant_model_unavailable"
    assert "gemini-3.6-flash" in translated.message, (
        "the replacement model Google named must survive translation"
    )
    assert "MATHNOVA_AI_MODEL" in translated.message


def test_a_busy_model_is_a_retryable_message_not_a_generic_error():
    """
    Google's free tier returns 503 under load during normal use.

    It is transient and the right advice is "try again", which the
    generic provider-error message did not say.
    """

    from backend.assistant.providers.gemini import GeminiProvider

    raw = (
        "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is "
        "currently experiencing high demand. Spikes in demand are usually "
        "temporary. Please try again later.', 'status': 'UNAVAILABLE'}}"
    )

    translated = GeminiProvider()._translate(RuntimeError(raw))

    assert translated.status == 503
    assert translated.code == "assistant_busy"
    assert "again" in translated.message.lower()


def test_gemini_loop_is_bounded_and_reports_truncation(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    from backend.assistant.tools import TOOLS

    # Never stops asking for a tool: the provider must stop it.
    server, recorded = _stub_gemini([
        [{"functionCall": {"name": "differentiate_expression",
                           "args": {"expression": "x^2"}}}],
    ])

    try:
        provider = _gemini_provider(server)
        result = provider.chat(
            system="test",
            messages=[{"role": "user", "content": "loop"}],
            tools=TOOLS,
            max_tool_turns=4,
        )
    finally:
        server.shutdown()

    assert len(recorded) == 4, f"loop ran {len(recorded)} turns against a cap of 4"
    assert result.truncated is True


def test_service_fills_in_a_reply_when_the_loop_is_truncated(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "gemini")
    monkeypatch.setenv("MATHNOVA_ASSISTANT_MAX_TOOL_TURNS", "2")

    server, _ = _stub_gemini([
        [{"functionCall": {"name": "differentiate_expression",
                           "args": {"expression": "x^2"}}}],
    ])

    from backend.assistant import service
    from backend.config import settings

    monkeypatch.setattr(settings, "ASSISTANT_MAX_TOOL_TURNS", 2)
    monkeypatch.setenv(
        "MATHNOVA_GEMINI_BASE_URL",
        f"http://127.0.0.1:{server.server_address[1]}",
    )

    try:
        payload = service.chat("go")
    finally:
        server.shutdown()

    assert payload["truncated"] is True
    assert "tool steps" in payload["reply"]

    # The reply says which engines ran, never which model wrote it.
    assert "provider" not in payload
    assert "model" not in payload


# ---------------------------------------------------------
# Local provider
# ---------------------------------------------------------

def test_local_provider_is_off_unless_explicitly_enabled(monkeypatch):
    from backend.assistant.providers.local import LocalProvider

    monkeypatch.delenv("MATHNOVA_LOCAL_AI_ENABLED", raising=False)

    assert LocalProvider.is_configured() is False


def test_local_provider_runs_the_tool_loop(monkeypatch):
    """The offline path must drive the same engines."""

    import json
    import socketserver
    import threading
    from http.server import BaseHTTPRequestHandler

    recorded = []
    turns = [
        {"role": "assistant", "tool_calls": [
            {"function": {"name": "compute_z_transform",
                          "arguments": {"sequence": "a^n"}}}
        ]},
        {"role": "assistant", "content": "X(z) = z/(z-a)."},
    ]

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            recorded.append(json.loads(self.rfile.read(length)))

            body = json.dumps({
                "message": turns[min(len(recorded) - 1, len(turns) - 1)]
            }).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    from backend.assistant.providers.local import LocalProvider
    from backend.assistant.tools import TOOLS

    try:
        provider = LocalProvider(
            base_url=f"http://127.0.0.1:{server.server_address[1]}",
            model="llama3.1",
        )
        result = provider.chat(
            system="test",
            messages=[{"role": "user", "content": "Z transform of a^n"}],
            tools=TOOLS,
            max_tool_turns=6,
        )
    finally:
        server.shutdown()

    assert result.provider == "local"
    assert result.tools_used == ["compute_z_transform"]
    assert "z/(z-a)" in result.reply

    # The engine's verified answer must be fed back to the model.
    sent = json.dumps(recorded[1])
    assert "-z/(a - z)" in sent, "the engine result never reached the model"
    assert '"role": "tool"' in sent


def test_local_provider_reports_an_unreachable_server():
    from backend.assistant.providers.base import NotConfigured
    from backend.assistant.providers.local import LocalProvider

    provider = LocalProvider(base_url="http://127.0.0.1:1", timeout=2)

    with pytest.raises(NotConfigured):
        provider.chat(system="t", messages=[{"role": "user", "content": "hi"}],
                      tools=[], max_tool_turns=1)


# ---------------------------------------------------------
# Registry
# ---------------------------------------------------------

def test_status_never_claims_a_provider_that_chat_would_reject(monkeypatch):
    """
    The panel's "ready" line and the chat endpoint must agree.

    Selecting an unconfigured provider while another one happens to have
    credentials previously reported enabled, then failed on send.
    """

    from backend.assistant import providers

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "local")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    status = providers.status()

    assert status["enabled"] is False
    assert status["setup_hint"]
    assert client.post(
        "/api/assistant/chat", json={"message": "hi"}
    ).status_code == 503


def test_registry_prefers_gemini_then_local(monkeypatch):
    from backend.assistant import providers

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    assert providers.resolve().name == "gemini"

    status = providers.status()
    assert status["enabled"] is True
    assert status["provider"] == "gemini"
    assert status["setup_hint"] is None


# =========================================================
# SERIALIZATION
# =========================================================

def test_serialize_handles_engine_shapes():
    import numpy as np
    import sympy as sp

    from backend.serialization import serialize

    x = sp.Symbol("x")

    payload = serialize({
        "expression": x ** 2 + 1,
        "matrix": sp.Matrix([[1, 2], [3, 4]]),
        "flag": sp.true,
        "array": np.array([1.5, 2.5]),
        "scalar": np.float64(3.25),
        "nested": [{"inner": sp.sin(x)}],
        "plain": 7,
        "nothing": None
    })

    assert payload["expression"]["text"] == "x**2 + 1"
    assert payload["matrix"]["rows"] == 2
    assert payload["flag"] is True
    assert payload["array"] == [1.5, 2.5]
    assert payload["scalar"] == 3.25
    assert payload["nested"][0]["inner"]["latex"] == r"\sin{\left(x \right)}"
    assert payload["plain"] == 7
    assert payload["nothing"] is None


def test_serialize_replaces_non_finite_numbers():
    from backend.serialization import serialize

    assert serialize(float("nan")) is None
    assert serialize(float("inf")) is None

