"""
Bounded execution for the symbolic engines.

Symbolic mathematics has no useful upper bound on cost. `integrate`
against a pathological integrand, or an expansion like (x+1)**10**9,
can run for hours or exhaust memory, and neither input looks unusual:
they are short strings that pass every length check. A request-size
limit cannot catch them, because the cost is in the mathematics rather
than in the bytes.

So every engine call runs in a forked child process with a wall-clock
deadline and an address-space cap. If it overruns, the child is killed
and the request fails cleanly; the worker serving the request is never
the process doing the work, so it cannot be hung or OOM-killed by one
bad input.

Fork costs about a millisecond here and copies no memory up front, which
is cheap next to the engines themselves (a routine Laplace transform is
~85ms). Where fork is unavailable — Windows, and any platform whose only
start methods are spawn-based — the call runs in-process instead: the
deadline cannot be enforced, so the limits in the request models are the
only guard. That is a development-only situation; the Docker image and
every supported deploy target are Linux.
"""

import logging
import multiprocessing
import os
import pickle
import signal

from backend.config import settings

logger = logging.getLogger("mathnova.compute")

# Fork is what makes this cheap: the child inherits the parent's memory,
# so neither the engine function nor its arguments has to be picklable —
# only the result travels back, over a pipe.
_FORK_AVAILABLE = "fork" in multiprocessing.get_all_start_methods()

_CONTEXT = multiprocessing.get_context("fork") if _FORK_AVAILABLE else None

#: Exception types worth preserving across the process boundary. Anything
#: else degrades to ValueError, which `errors.solve()` reads as bad input
#: — the right default for a failure raised by an engine.
_RECOVERABLE = {
    cls.__name__: cls
    for cls in (
        ValueError,
        TypeError,
        SyntaxError,
        ZeroDivisionError,
        ArithmeticError,
        OverflowError,
        IndexError,
        KeyError,
        AttributeError,
        NotImplementedError,
        RecursionError,
        MemoryError,
    )
}


class ComputationTimeout(Exception):
    """An engine call exceeded its wall-clock deadline."""


class ComputationTooLarge(Exception):
    """An engine call exhausted its memory allowance."""


class ResultNotTransferable(Exception):
    """
    The engine returned a live Python object, not a value.

    A lambdified callable cannot cross a process boundary. Such a call
    belongs outside the guard — see `errors.solve(isolated=False)` —
    so this is a programming error, never bad input from a client.
    """


def _apply_child_limits():
    """
    Cap the child's own resources.

    The deadline alone is not enough: a memory bomb can drive the host
    into swap long before it expires, which degrades every other request.
    An address-space cap turns that into a prompt MemoryError instead.
    """

    try:
        import resource
    except ImportError:  # pragma: no cover - POSIX only
        return

    limit = settings.COMPUTE_MEMORY_MB * 1024 * 1024

    for name in ("RLIMIT_AS", "RLIMIT_DATA"):
        constant = getattr(resource, name, None)

        if constant is None:
            continue

        try:
            soft, hard = resource.getrlimit(constant)
            ceiling = limit if hard in (resource.RLIM_INFINITY,) else min(limit, hard)
            resource.setrlimit(constant, (ceiling, hard))
        except (ValueError, OSError):  # pragma: no cover - platform dependent
            # A limit we cannot lower is not a reason to fail the request;
            # the deadline still applies.
            pass


def _child(pipe, function, args, kwargs):
    """Run the engine and hand the outcome back down the pipe."""

    # Die on the parent's terms, not on an inherited handler.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    _apply_child_limits()

    try:
        payload = ("ok", function(*args, **kwargs))
    except BaseException as error:  # noqa: BLE001 - relayed, not swallowed
        payload = ("error", error)

    try:
        pipe.send_bytes(pickle.dumps(payload))
    except Exception:  # noqa: BLE001 - result or exception would not pickle
        kind, value = payload

        if kind == "ok":
            fallback = ("unpicklable", type(value).__name__)
        else:
            fallback = ("raised", type(value).__name__, str(value))

        try:
            pipe.send_bytes(pickle.dumps(fallback))
        except Exception:  # noqa: BLE001 - nothing more we can do
            pass
    finally:
        pipe.close()

    # Skip interpreter teardown: atexit hooks and flushes belong to the
    # parent, and running them in a forked child can deadlock.
    os._exit(0)


def _reraise(payload):
    """Turn a relayed outcome back into a value or an exception."""

    if payload[0] == "ok":
        return payload[1]

    if payload[0] == "error":
        raise payload[1]

    if payload[0] == "unpicklable":
        raise ResultNotTransferable(payload[1])

    _, name, message = payload

    raise _RECOVERABLE.get(name, ValueError)(message)


def run_guarded(function, *args, timeout=None, **kwargs):
    """
    Call `function` under a wall-clock deadline and a memory cap.

    Returns its result, re-raises whatever it raised, or raises
    ComputationTimeout / ComputationTooLarge. Exceptions keep their type
    where it matters, so the existing error translation in
    `errors.solve()` continues to classify them.
    """

    timeout = timeout or settings.COMPUTE_TIMEOUT

    if not _FORK_AVAILABLE:
        # No isolation available. Documented in the module docstring;
        # the request models still bound the input.
        return function(*args, **kwargs)

    receiver, sender = _CONTEXT.Pipe(duplex=False)
    process = _CONTEXT.Process(
        target=_child, args=(sender, function, args, kwargs), daemon=True
    )
    process.start()

    # The parent holds no copy of the write end, so the pipe reports EOF
    # as soon as the child dies — otherwise poll() would block for the
    # whole deadline on a child that crashed immediately.
    sender.close()

    try:
        ready = receiver.poll(timeout)

        if not ready:
            logger.warning(
                "Calculation exceeded %ss; terminating worker", timeout
            )
            raise ComputationTimeout(timeout)

        try:
            payload = pickle.loads(receiver.recv_bytes())
        except EOFError:
            # Child died without reporting: almost always the address
            # space cap, which the kernel enforces without warning.
            raise ComputationTooLarge()

        if payload[0] == "error" and isinstance(payload[1], MemoryError):
            raise ComputationTooLarge()

        return _reraise(payload)

    finally:
        receiver.close()
        _terminate(process)


def _terminate(process):
    """Stop the child, escalating if it ignores the polite signal."""

    if process.is_alive():
        process.terminate()
        process.join(2)

    if process.is_alive():  # pragma: no cover - only a wedged child
        try:
            os.kill(process.pid, signal.SIGKILL)
        except OSError:
            pass
        process.join(1)

    # Reap it so the process table does not fill with zombies.
    if not process.is_alive():
        process.close()
