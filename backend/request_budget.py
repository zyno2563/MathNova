"""One cooperative deadline shared by every calculation in an HTTP request."""

from contextvars import ContextVar
from threading import Event
from time import monotonic


class RequestStopped(Exception):
    def __init__(self, cancelled=False):
        self.cancelled = cancelled
        super().__init__("Request cancelled" if cancelled else "Request deadline exceeded")


class Budget:
    def __init__(self, seconds):
        self.deadline = monotonic() + seconds
        self.cancelled = Event()

    def remaining(self):
        if self.cancelled.is_set():
            raise RequestStopped(cancelled=True)
        seconds = self.deadline - monotonic()
        if seconds <= 0:
            raise RequestStopped()
        return seconds


current_budget = ContextVar("mathnova_request_budget", default=None)


def check_budget():
    budget = current_budget.get()
    return budget.remaining() if budget else None
