"""Exercise overload, queue recovery, disconnects and shared request budgets."""
import asyncio
import json
import multiprocessing
import time

import pytest

from backend.admission import AdmissionMiddleware
from backend.config import settings
from backend.compute import ComputationTimeout, run_guarded
from backend.request_budget import Budget, RequestStopped, current_budget


def connection(app, path='/api/work', peer='192.0.2.1', method='POST', headers=None):
    incoming = asyncio.Queue()
    incoming.put_nowait({'type': 'http.request', 'body': b'{}', 'more_body': False})
    sent = []
    async def send(message):
        sent.append(message)
    scope = {'type': 'http', 'path': path, 'method': method, 'client': (peer, 1000), 'headers': headers or []}
    task = asyncio.create_task(app(scope, incoming.get, send))
    return task, incoming, sent


def status(messages):
    return next(item['status'] for item in messages if item['type'] == 'http.response.start')


async def respond(send):
    await send({'type': 'http.response.start', 'status': 200, 'headers': []})
    await send({'type': 'http.response.body', 'body': b'{}'})


async def until(predicate):
    async def poll():
        while not predicate():
            await asyncio.sleep(.005)
    await asyncio.wait_for(poll(), 2)


def test_queue_is_bounded_health_stays_available_and_capacity_recovers(monkeypatch):
    monkeypatch.setattr(settings, 'MAX_ACTIVE_REQUESTS', 1)
    monkeypatch.setattr(settings, 'MAX_QUEUED_REQUESTS', 1)
    async def scenario():
        release = asyncio.Event()
        async def app(scope, receive, send):
            if scope['method'] == 'POST':
                await release.wait()
            await respond(send)
        middleware = AdmissionMiddleware(app)
        first, _, first_messages = connection(middleware)
        await until(lambda: middleware.active == 1)
        second, _, second_messages = connection(middleware)
        await until(lambda: len(middleware.queue) == 1)
        third, _, third_messages = connection(middleware)
        await third
        assert status(third_messages) == 503
        assert dict(third_messages[0]['headers'])[b'retry-after'] == b'2'
        health, _, health_messages = connection(middleware, '/api/health', method='GET')
        await health
        assert status(health_messages) == 200
        release.set()
        await asyncio.gather(first, second)
        assert status(first_messages) == status(second_messages) == 200
        assert middleware.active == 0 and not middleware.queue
    asyncio.run(scenario())


def test_visitor_limits_ignore_untrusted_forwarded_headers_and_ai_has_global_cap(monkeypatch):
    monkeypatch.setattr(settings, 'REQUESTS_PER_MINUTE', 1)
    monkeypatch.setattr(settings, 'AI_GLOBAL_REQUESTS_PER_MINUTE', 2)
    async def scenario():
        async def app(scope, receive, send):
            await respond(send)
        middleware = AdmissionMiddleware(app)
        first, _, messages = connection(middleware)
        await first
        assert status(messages) == 200
        second, _, messages = connection(middleware, headers=[(b'x-forwarded-for', b'203.0.113.99')])
        await second
        assert status(messages) == 429
        for index in range(3):
            request, _, messages = connection(middleware, '/api/assistant/chat', peer=f'192.0.2.{index+10}')
            await request
            assert status(messages) == (200 if index < 2 else 429)
    asyncio.run(scenario())


def test_queue_timeout_and_disconnect_do_not_leak_slots(monkeypatch):
    monkeypatch.setattr(settings, 'MAX_ACTIVE_REQUESTS', 1)
    monkeypatch.setattr(settings, 'QUEUE_WAIT_SECONDS', .08)
    async def scenario():
        release = asyncio.Event()
        async def app(scope, receive, send):
            await release.wait()
            await respond(send)
        middleware = AdmissionMiddleware(app)
        first, _, _ = connection(middleware)
        await until(lambda: middleware.active == 1)
        second, _, messages = connection(middleware)
        await second
        assert status(messages) == 503
        assert not middleware.queue
        third, incoming, messages = connection(middleware)
        await until(lambda: len(middleware.queue) == 1)
        await incoming.put({'type': 'http.disconnect'})
        await third
        assert not middleware.queue and not messages
        release.set()
        await first
        assert middleware.active == 0
    asyncio.run(scenario())


def test_disconnect_stops_running_child_and_frees_capacity():
    async def scenario():
        started = asyncio.Event()
        async def app(scope, receive, send):
            started.set()
            await asyncio.to_thread(run_guarded, time.sleep, 5)
            await respond(send)
        middleware = AdmissionMiddleware(app)
        before = {child.pid for child in multiprocessing.active_children()}
        task, incoming, _ = connection(middleware)
        await started.wait()
        await asyncio.sleep(.1)
        await incoming.put({'type': 'http.disconnect'})
        await asyncio.wait_for(task, 1)
        assert middleware.active == 0
        assert {child.pid for child in multiprocessing.active_children()} <= before
    asyncio.run(scenario())


def test_deadline_is_shared_across_sequential_engine_calls():
    token = current_budget.set(Budget(.25))
    started = time.monotonic()
    try:
        run_guarded(time.sleep, .15)
        with pytest.raises((RequestStopped, ComputationTimeout)):
            run_guarded(time.sleep, 2)
    finally:
        current_budget.reset(token)
    assert time.monotonic() - started < 1


def test_assistant_errors_survive_isolation():
    from backend.errors import EngineError
    def unavailable():
        raise EngineError(429, 'assistant_daily_limit', 'Please try again tomorrow.')
    with pytest.raises(EngineError) as raised:
        run_guarded(unavailable)
    assert raised.value.status_code == 429
    assert raised.value.code == 'assistant_daily_limit'


def test_real_app_rate_rejections_have_security_and_retry_headers(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    monkeypatch.setattr(settings, 'REQUESTS_PER_MINUTE', 1)
    with TestClient(create_app()) as client:
        assert client.post('/api/calculus/differentiate', json={'expression': 'x^2'}).status_code == 200
        response = client.post('/api/calculus/differentiate', json={'expression': 'x^2'})
        assert response.status_code == 429
        assert response.json()['error']['code'] == 'rate_limited'
        assert response.headers['Retry-After']
        assert response.headers['Content-Security-Policy']
        assert client.get('/api/health').status_code == 200
