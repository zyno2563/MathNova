"""
Response headers that constrain what a browser will do with a page.

The policy is written against what the frontend actually loads — one
CDN, for KaTeX — rather than copied from a template. `tests/
test_hardening.py` re-derives the external origins from index.html and
fails if the two ever drift, so adding a script tag cannot silently
leave the page half-broken in production.

KaTeX is the reason `style-src` allows inline styles: it renders maths
by writing `style` attributes onto the elements it produces, and those
are governed by style-src. Scripts get no such exemption.
"""

CDN = "https://cdn.jsdelivr.net"

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    f"script-src 'self' {CDN}",
    f"style-src 'self' {CDN} 'unsafe-inline'",
    f"font-src 'self' {CDN} data:",
    "img-src 'self' data:",
    # The API is same-origin. A page that starts talking to somewhere
    # else is not something this app does.
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    # Stop a browser from second-guessing a declared content type, which
    # is how a JSON response gets treated as HTML and executed.
    "X-Content-Type-Options": "nosniff",
    # Belt-and-braces alongside frame-ancestors, for older browsers.
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # The app asks for no device permissions at all.
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class SecurityHeadersMiddleware:
    """Attach the headers to every response, including error responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                present = {name.lower() for name, _ in headers}

                for name, value in HEADERS.items():
                    if name.lower().encode() not in present:
                        headers.append((name.lower().encode(), value.encode()))

            await send(message)

        await self.app(scope, receive, send_with_headers)
