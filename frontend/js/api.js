/**
 * Thin client for the MathNova REST API.
 *
 * Every endpoint answers with {ok, result} or {ok:false, error:{code,message}},
 * so callers only ever see a resolved result or a thrown ApiError.
 */

export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code || 'error';
    this.status = status || 0;
  }
}

async function request(path, options = {}) {
  const { timeoutMs = 120000, signal, ...fetchOptions } = options;
  const controller = new AbortController();
  let timedOut = false;
  const cancel = () => controller.abort();
  if (signal?.aborted) cancel();
  else signal?.addEventListener('abort', cancel, { once: true });
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    return await readResponse(path, { ...fetchOptions, signal: controller.signal });
  } catch (cause) {
    if (controller.signal.aborted) {
      throw new ApiError(
        timedOut
          ? 'The server took too long to respond. It may be waking up or busy. Please try again.'
          : 'The request was cancelled. You can edit your input and try again.',
        timedOut ? 'request_timeout' : 'request_cancelled',
        0
      );
    }
    throw cause;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}

async function readResponse(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (cause) {
    throw new ApiError(
      'Could not reach the MathNova server. Check that it is running.',
      'network_error',
      0
    );
  }

  let payload = null;

  try {
    payload = await response.json();
  } catch (cause) {
    throw new ApiError(
      `The server returned an unreadable response (HTTP ${response.status}).`,
      'bad_response',
      response.status
    );
  }

  if (!response.ok || !payload || payload.ok !== true) {
    const error = (payload && payload.error) || {};
    throw new ApiError(
      error.message || `Request failed (HTTP ${response.status}).`,
      error.code,
      response.status
    );
  }

  return payload.result;
}

export function post(path, body, options = {}) {
  return request(path, {
    ...options,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}

export function get(path, options = {}) {
  return request(path, { ...options, method: 'GET' });
}
