"""
The Groq provider, and falling through providers when one runs out.

Every test runs against local stub servers — no key, no network, no
quota — speaking the same wire formats the real services do.
"""

import json
import socketserver
import threading
from http.server import BaseHTTPRequestHandler

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

SCREENSHOT_QUESTION = "Solve the ODE y'' - 3y' + 2y = 0"


def _stub(respond):
    """
    Serve POSTs with `respond(body, recorded) -> (status, payload)`.

    Returns the server, its base URL and the list of recorded requests.
    """

    recorded = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            recorded.append({
                "path": self.path,
                "auth": self.headers.get("Authorization"),
                "body": body,
            })

            status, payload = respond(body, recorded)
            data = json.dumps(payload).encode()

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    return server, f"http://127.0.0.1:{server.server_address[1]}", recorded


def _reply(content=None, tool_calls=None):
    message = {"role": "assistant", "content": content}

    if tool_calls:
        message["tool_calls"] = tool_calls

    return 200, {"choices": [{"index": 0, "message": message,
                              "finish_reason": "stop"}]}


def _limit(kind="tokens per day (TPD)"):
    return 429, {"error": {
        "message": f"Rate limit reached on {kind}: Limit 200000, Used 200000",
        "type": "tokens", "code": "rate_limit_exceeded",
    }}


def _tool_call(name, arguments, call_id="call_1"):
    return [{"id": call_id, "type": "function",
             "function": {"name": name, "arguments": json.dumps(arguments)}}]


@pytest.fixture
def groq(monkeypatch):
    """Configure Groq to talk to a stub; returns a function to start one."""

    servers = []

    def start(respond, models="model-a,model-b"):
        server, url, recorded = _stub(respond)
        servers.append(server)

        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        monkeypatch.setenv("MATHNOVA_GROQ_BASE_URL", url)
        monkeypatch.setenv("MATHNOVA_GROQ_MODELS", models)

        return recorded

    yield start

    for server in servers:
        server.shutdown()


# =========================================================
# The Groq provider itself
# =========================================================

def test_groq_runs_the_engines_and_feeds_their_answer_back(groq):
    """The whole point: the model calls MathNova, not its own algebra."""

    def respond(body, recorded):
        if len(recorded) == 1:
            return _reply(tool_calls=_tool_call(
                "compute_laplace_transform", {"function": "t^2*exp(-3*t)"}))
        return _reply("The transform is $\\frac{2}{(s+3)^3}$.")

    recorded = groq(respond)

    from backend.assistant.providers.groq import GroqProvider
    from backend.assistant.service import SYSTEM_PROMPT
    from backend.assistant.tools import TOOLS

    result = GroqProvider().chat(
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "Laplace of t^2 e^-3t"}],
        tools=TOOLS,
    )

    assert result.tools_used == ["compute_laplace_transform"]
    assert "(s+3)^3" in result.reply

    first = recorded[0]
    assert first["path"] == "/chat/completions"
    assert first["auth"] == "Bearer test-groq-key"
    assert first["body"]["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert len(first["body"]["tools"]) == len(TOOLS)

    # The engine's verified result, not the model's, reaches the reply.
    tool_turn = recorded[1]["body"]["messages"][-1]
    assert tool_turn["role"] == "tool"
    assert tool_turn["tool_call_id"] == "call_1"
    assert "2/(s + 3)**3" in tool_turn["content"]


def test_groq_asks_for_an_output_size_its_free_tier_accepts(groq):
    """
    Groq checks prompt + max output against a per-minute token limit of
    a few thousand. The app-wide 16,000 would be refused every time.
    """

    recorded = groq(lambda body, rec: _reply("ok"))

    from backend.assistant.providers.groq import DEFAULT_MAX_TOKENS, GroqProvider

    GroqProvider().chat(system="s", messages=[{"role": "user", "content": "hi"}],
                        tools=[], max_output_tokens=16000)

    assert recorded[0]["body"]["max_tokens"] == DEFAULT_MAX_TOKENS
    assert DEFAULT_MAX_TOKENS <= 4096


def test_groq_moves_to_the_next_model_when_one_hits_its_limit(groq):
    """Free-tier limits are per model, so the next one has its own."""

    def respond(body, recorded):
        if body["model"] == "model-a":
            return _limit()
        return _reply("answered by b")

    recorded = groq(respond)

    from backend.assistant.providers.groq import GroqProvider

    result = GroqProvider().chat(
        system="s", messages=[{"role": "user", "content": "hi"}], tools=[])

    assert result.reply == "answered by b"
    assert result.model == "model-b"
    assert [r["body"]["model"] for r in recorded] == ["model-a", "model-b"]


def test_groq_with_every_model_spent_reports_a_daily_limit(groq):
    groq(lambda body, rec: _limit("requests per day (RPD)"))

    from backend.assistant.providers.base import ProviderError
    from backend.assistant.providers.groq import GroqProvider

    with pytest.raises(ProviderError) as raised:
        GroqProvider().chat(
            system="s", messages=[{"role": "user", "content": "hi"}], tools=[])

    assert raised.value.code == "assistant_daily_limit"


def test_a_per_minute_limit_is_not_reported_as_daily(groq):
    groq(lambda body, rec: _limit("tokens per minute (TPM)"))

    from backend.assistant.providers.base import ProviderError
    from backend.assistant.providers.groq import GroqProvider

    with pytest.raises(ProviderError) as raised:
        GroqProvider().chat(
            system="s", messages=[{"role": "user", "content": "hi"}], tools=[])

    assert raised.value.code == "assistant_rate_limited"


def test_a_rejected_groq_key_is_reported_as_not_configured(groq):
    groq(lambda body, rec: (401, {"error": {"message": "Invalid API Key"}}))

    from backend.assistant.providers.base import NotConfigured
    from backend.assistant.providers.groq import GroqProvider

    with pytest.raises(NotConfigured):
        GroqProvider().chat(
            system="s", messages=[{"role": "user", "content": "hi"}], tools=[])


# =========================================================
# Choosing and falling through providers
# =========================================================

def test_groq_leads_when_configured(groq, monkeypatch):
    groq(lambda body, rec: _reply("ok"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")

    from backend.assistant import providers

    assert [p.name for p in providers.chain()][:2] == ["groq", "gemini"]


def test_an_explicit_choice_is_never_widened(groq, monkeypatch):
    groq(lambda body, rec: _reply("ok"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "gemini")

    from backend.assistant import providers

    assert [p.name for p in providers.chain()] == ["gemini"]


def test_when_groq_is_spent_gemini_answers(groq, monkeypatch):
    """The whole fall-through, through the real HTTP route."""

    groq(lambda body, rec: _limit())

    gemini_server, gemini_url, gemini_seen = _stub(lambda body, rec: (200, {
        "candidates": [{"content": {"role": "model",
                                    "parts": [{"text": "Gemini answered."}]},
                        "finishReason": "STOP"}]
    }))

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_GEMINI_BASE_URL", gemini_url)
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    try:
        response = client.post(
            "/api/assistant/chat", json={"message": SCREENSHOT_QUESTION})
    finally:
        gemini_server.shutdown()

    assert response.status_code == 200, response.text
    assert response.json()["result"]["reply"] == "Gemini answered."
    assert gemini_seen, "Gemini was never asked"


def test_when_every_provider_is_spent_the_message_says_today(groq, monkeypatch):
    """
    Regression: this used to read "busy right now, wait a moment",
    which is wrong for a limit that only resets the next day.
    """

    groq(lambda body, rec: _limit())

    gemini_server, gemini_url, _ = _stub(lambda body, rec: (429, {
        "error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                  "message": "Quota exceeded for quota id "
                             "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}
    }))

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_GEMINI_BASE_URL", gemini_url)
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    try:
        response = client.post(
            "/api/assistant/chat", json={"message": SCREENSHOT_QUESTION})
    finally:
        gemini_server.shutdown()

    assert response.status_code == 429

    error = response.json()["error"]
    assert error["code"] == "assistant_daily_limit"
    assert "today" in error["message"]
    assert "wait a moment" not in error["message"]

    for vendor in ("groq", "gemini", "google"):
        assert vendor not in error["message"].lower()


def test_a_short_limit_anywhere_beats_reporting_a_daily_one(groq, monkeypatch):
    """If any provider might answer soon, "try later today" is too bleak."""

    groq(lambda body, rec: _limit("tokens per minute (TPM)"))

    gemini_server, gemini_url, _ = _stub(lambda body, rec: (429, {
        "error": {"code": 429, "message": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}
    }))

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("MATHNOVA_GEMINI_BASE_URL", gemini_url)
    monkeypatch.setenv("MATHNOVA_AI_PROVIDER", "auto")
    monkeypatch.setenv("MATHNOVA_LOCAL_AI_ENABLED", "0")

    try:
        response = client.post("/api/assistant/chat", json={"message": "hi"})
    finally:
        gemini_server.shutdown()

    assert response.json()["error"]["code"] == "assistant_rate_limited"


def test_gemini_names_its_daily_quota_correctly():
    from backend.assistant.providers.gemini import GeminiProvider

    daily = GeminiProvider()._translate(RuntimeError(
        "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'details': "
        "[{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]}}"
    ))
    minute = GeminiProvider()._translate(RuntimeError(
        "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'details': "
        "[{'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier'}]}}"
    ))

    assert daily.code == "assistant_daily_limit"
    assert minute.code == "assistant_rate_limited"
