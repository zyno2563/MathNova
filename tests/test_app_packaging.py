"""
What the Android (Trusted Web Activity) build depends on.

The Play Store app is this website, installed: the packager reads the
manifest, the icons and the service worker from the live site. If any
of them breaks, the next app build breaks — and nothing in the web UI
would look wrong — so each requirement is pinned here.
"""

import glob
import json
import os
import re
import struct

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)


def manifest():
    with open(os.path.join(FRONTEND, "manifest.json"), encoding="utf-8") as handle:
        return json.load(handle)


def png_size(path):
    """Width and height from a PNG's IHDR chunk — no image library needed."""

    with open(path, "rb") as handle:
        header = handle.read(24)

    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"

    return struct.unpack(">II", header[16:24])


def pages():
    return sorted(
        glob.glob(os.path.join(FRONTEND, "index.html"))
        + glob.glob(os.path.join(FRONTEND, "*", "index.html"))
    )


# =========================================================
# Manifest
# =========================================================

def test_the_manifest_has_what_an_installable_app_needs():
    data = manifest()

    for field in ("name", "short_name", "start_url", "scope", "display",
                  "icons", "theme_color", "background_color"):
        assert data.get(field), f"manifest is missing {field}"

    assert data["display"] == "standalone"
    assert len(data["short_name"]) <= 12, "short_name is cut off on launchers"
    assert data["start_url"].startswith(data["scope"])


def test_the_manifest_declares_the_icon_sizes_the_store_requires():
    icons = manifest()["icons"]

    sizes = {(icon["sizes"], icon.get("purpose", "any")) for icon in icons}

    assert ("192x192", "any") in sizes
    assert ("512x512", "any") in sizes
    assert ("512x512", "maskable") in sizes, (
        "Android crops launcher icons; without a maskable one it shrinks "
        "the icon into a white circle"
    )


def test_every_declared_icon_exists_at_its_declared_size():
    entries = list(manifest()["icons"])

    for shortcut in manifest().get("shortcuts", []):
        entries.extend(shortcut.get("icons", []))

    for icon in entries:
        path = os.path.join(FRONTEND, icon["src"].lstrip("/"))

        assert os.path.isfile(path), f"missing icon {icon['src']}"

        width, height = map(int, icon["sizes"].split("x"))
        assert png_size(path) == (width, height), (
            f"{icon['src']} is {png_size(path)}, declared {icon['sizes']}"
        )


def test_the_start_url_and_shortcuts_open_real_pages():
    data = manifest()

    targets = [data["start_url"]] + [s["url"] for s in data.get("shortcuts", [])]

    for url in targets:
        assert client.get(url).status_code == 200, f"{url} does not load"


def test_the_manifest_is_served_as_json():
    response = client.get("/manifest.json")

    assert response.status_code == 200
    assert "json" in response.headers["content-type"]


# =========================================================
# Pages
# =========================================================

def test_every_page_links_the_manifest_and_matching_theme_colour():
    theme = manifest()["theme_color"]

    for path in pages():
        html = open(path, encoding="utf-8").read()
        route = os.path.relpath(path, FRONTEND)

        assert '<link rel="manifest" href="/manifest.json"' in html, route
        assert f'<meta name="theme-color" content="{theme}"' in html, (
            f"{route}: theme-color must match the manifest, or the status "
            f"bar changes colour between the splash screen and the page"
        )
        assert 'rel="apple-touch-icon"' in html, route


def test_every_linked_icon_exists():
    for path in pages() + [os.path.join(FRONTEND, "offline.html")]:
        html = open(path, encoding="utf-8").read()

        for href in re.findall(r'(?:href|src)="(/icons/[^"]+)"', html):
            assert os.path.isfile(os.path.join(FRONTEND, href.lstrip("/"))), (
                f"{os.path.relpath(path, FRONTEND)} links missing {href}"
            )


# =========================================================
# Service worker
# =========================================================

def test_the_service_worker_is_served_from_the_root():
    """A worker only controls pages at or below its own path."""

    response = client.get("/sw.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_the_service_worker_never_caches_a_calculation():
    """
    A cached calculation is a wrong answer waiting to happen: the next
    request for the same input would skip the engines entirely.
    """

    source = open(os.path.join(FRONTEND, "sw.js"), encoding="utf-8").read()

    assert "url.pathname.startsWith('/api/')" in source
    assert "request.method !== 'GET'" in source, (
        "POST requests (every calculation) must bypass the worker"
    )


def test_the_service_worker_is_network_first():
    """Cache-first would hide every deploy behind a stale copy."""

    source = open(os.path.join(FRONTEND, "sw.js"), encoding="utf-8").read()

    assert "networkFirst" in source
    assert "caches.match(request)" in source.split("catch")[1], (
        "the cache must only be consulted after the network fails"
    )


def test_everything_the_worker_precaches_exists():
    source = open(os.path.join(FRONTEND, "sw.js"), encoding="utf-8").read()

    block = re.search(r"const PRECACHE = \[(.*?)\];", source, re.S).group(1)
    listed = re.findall(r"'(/[^']+)'", block)

    # addAll() is all-or-nothing: one missing file and install fails.
    for url in listed + ["/offline.html"]:
        assert client.get(url).status_code == 200, f"precached {url} is missing"


def test_the_offline_page_obeys_the_content_security_policy():
    html = open(os.path.join(FRONTEND, "offline.html"), encoding="utf-8").read()

    assert "<script" not in html, "the CSP blocks inline script"
    assert not re.search(r'\son\w+\s*=', html), "inline handlers are blocked"


def test_the_csp_permits_the_manifest_and_the_worker():
    """Both fall back to default-src; neither may be restricted away."""

    from backend.security_headers import CONTENT_SECURITY_POLICY

    assert "default-src 'self'" in CONTENT_SECURITY_POLICY

    for directive in ("manifest-src", "worker-src"):
        assert directive not in CONTENT_SECURITY_POLICY or (
            f"{directive} 'self'" in CONTENT_SECURITY_POLICY
        )

    assert "script-src 'self'" in CONTENT_SECURITY_POLICY
