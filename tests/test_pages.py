"""
The V1 product layer: the pages, their navigation, and the one support
address.

Navigation is generated at runtime from frontend/js/pages.js, so these
tests read that manifest as the source of truth and check the site
against it — a page listed in the menu but never built, or built and
never linked, fails here rather than in someone's browser.
"""

import glob
import os
import re

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(REPO, "frontend")

#: The only address for bug reports and support.
SUPPORT_EMAIL = "b66475781@gmail.com"

#: Every page V1 ships, as (page id, route).
EXPECTED = [
    ("home", "/"),
    ("solver", "/solver/"),
    ("learn", "/learn/"),
    ("assistant", "/assistant/"),
    ("settings", "/settings/"),
    ("about", "/about/"),
    ("contact", "/contact/"),
    ("disclaimer", "/disclaimer/"),
    ("terms", "/terms/"),
    ("privacy", "/privacy/"),
]


def manifest():
    """The nav entries declared in frontend/js/pages.js."""

    source = open(os.path.join(FRONTEND, "js", "pages.js")).read()

    return re.findall(
        r"id:\s*'([^']+)',\s*\n?\s*href:\s*'([^']+)'", source
    )


def page_source(route):
    parts = [FRONTEND] + [part for part in route.split("/") if part]
    return open(os.path.join(*parts, "index.html"), encoding="utf-8").read()


def page_text(route):
    """Page source with runs of whitespace collapsed.

    Markup wraps prose across lines, so a phrase test against the raw
    source fails on where the line happened to break.
    """

    return " ".join(page_source(route).split()).lower()


def all_pages():
    return {route: page_source(route) for _, route in EXPECTED}


# =========================================================
# The pages exist and are served
# =========================================================

@pytest.mark.parametrize("page_id,route", EXPECTED)
def test_every_page_is_built_and_served(page_id, route):
    parts = [FRONTEND] + [part for part in route.split("/") if part]

    assert os.path.isfile(os.path.join(*parts, "index.html")), (
        f"{page_id} has no index.html"
    )

    response = client.get(route)

    assert response.status_code == 200, f"{route} returned {response.status_code}"
    assert "text/html" in response.headers["content-type"]


@pytest.mark.parametrize("route", [r for _, r in EXPECTED if r != "/"])
def test_routes_work_without_a_trailing_slash(route):
    """`/about` is what people type and what gets linked from elsewhere."""

    response = client.get(route.rstrip("/"), follow_redirects=True)

    assert response.status_code == 200


def test_no_page_was_built_that_the_site_map_does_not_list():
    """A stray page nothing links to is dead weight, not a feature."""

    built = set()

    for path in glob.glob(
        os.path.join(FRONTEND, "**", "index.html"), recursive=True
    ):
        route = os.path.relpath(path, FRONTEND)[: -len("index.html")]
        built.add("/" + route.replace(os.sep, "/"))

    assert built == {route for _, route in EXPECTED}


# =========================================================
# Navigation
# =========================================================

def test_the_site_map_and_the_built_pages_agree():
    declared = manifest()

    assert declared, "pages.js declares no navigation"

    assert {(page_id, href) for page_id, href in declared} == set(EXPECTED), (
        "pages.js and the built pages disagree about the site map"
    )


def test_every_navigation_target_resolves():
    for page_id, href in manifest():
        response = client.get(href)

        assert response.status_code == 200, (
            f"nav links to {href} ({page_id}), which returns "
            f"{response.status_code}"
        )


def test_every_page_declares_which_page_it_is():
    """
    The shared chrome marks the current link from `data-page`.

    A page whose id does not match its route would render with the wrong
    entry highlighted, or none at all.
    """

    for page_id, route in EXPECTED:
        html = page_source(route)

        found = re.search(r'<body data-page="([^"]+)"', html)

        assert found, f"{route} has no data-page on <body>"
        assert found.group(1) == page_id, (
            f"{route} declares data-page=\"{found.group(1)}\", expected "
            f"\"{page_id}\""
        )


def test_every_page_loads_the_shared_chrome_and_styles():
    for page_id, route in EXPECTED:
        html = page_source(route)

        assert '/css/styles.css' in html, f"{route} is missing the base styles"
        assert '/css/pages.css' in html, f"{route} is missing the page styles"

        # The solver boots itself through app.js, which mounts the shell;
        # every other page uses the shared entry point.
        entry = "/js/app.js" if page_id == "solver" else "/js/page.js"

        assert entry in html, f"{route} does not load {entry}"


def test_every_page_has_the_drawer_the_chrome_needs():
    """
    The chrome is injected into anchors the page must provide.

    Without them the navigation silently does not appear, which is the
    kind of fault that ships because the page still looks fine.
    """

    for _, route in EXPECTED:
        html = page_source(route)

        for anchor in ('id="site-nav"', 'id="sidebar"', 'id="scrim"',
                       'id="main"'):
            assert anchor in html, f"{route} is missing {anchor}"


def test_in_page_links_between_pages_all_resolve():
    """Body copy links to other pages; none of them may 404."""

    broken = []

    for _, route in EXPECTED:
        html = page_source(route)

        for href in set(re.findall(r'href="(/[^"#?]*)"', html)):
            if href.startswith(("/api/", "/css/", "/js/")):
                continue

            if client.get(href).status_code != 200:
                broken.append(f"{route} -> {href}")

    assert not broken, f"broken internal links: {broken}"


def test_the_solver_keeps_the_markup_its_script_drives():
    """The V1 restructure must not have cost the solver anything."""

    html = page_source("/solver/")

    for element_id in ("module-list", "module-title", "module-blurb",
                       "method-tabs", "method-form", "method-formula",
                       "results", "spinner", "submit-button",
                       "example-button"):
        assert f'id="{element_id}"' in html, (
            f"the solver page lost #{element_id}"
        )


# =========================================================
# Support address
# =========================================================

def test_the_support_address_is_on_the_contact_page():
    html = page_source("/contact/")

    assert SUPPORT_EMAIL in html
    assert f'href="mailto:{SUPPORT_EMAIL}"' in html, (
        "the address must be a mailto link, not just text"
    )


def test_the_support_address_is_declared_once_for_the_whole_site():
    """
    The footer renders it on every page from this one constant.

    Hard-coding it per page is how one of them ends up stale.
    """

    source = open(os.path.join(FRONTEND, "js", "pages.js")).read()

    assert f"SUPPORT_EMAIL = '{SUPPORT_EMAIL}'" in source


def test_the_address_appears_wherever_a_bug_would_be_reported():
    for route in ("/contact/", "/about/", "/disclaimer/", "/terms/",
                  "/privacy/", "/settings/", "/"):
        assert SUPPORT_EMAIL in page_source(route), (
            f"{route} discusses support but does not give the address"
        )


def test_no_other_support_address_exists_anywhere():
    """
    One address, and only one.

    A second address on a page nobody maintains sends reports into a
    void, so the whole repository is checked — not only the pages.
    """

    # A real address ends in an alphabetic TLD. Without that, package
    # pins like "katex@0.16.9" look like email addresses.
    pattern = re.compile(
        r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}", re.I
    )

    skip_dirs = {".git", ".venv", "node_modules", "__pycache__",
                 ".pytest_cache", "legacy"}

    offenders = []

    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for name in files:
            if not name.endswith((".html", ".js", ".css", ".py", ".md",
                                  ".yml", ".yaml", ".txt", ".json")):
                continue

            path = os.path.join(root, name)

            try:
                content = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue

            for address in pattern.findall(content):
                lowered = address.lower()

                if lowered == SUPPORT_EMAIL:
                    continue

                # Example addresses in policy copy and config samples are
                # not contact routes.
                if lowered.endswith((".example", "example.com",
                                     "example.org", "mathnova.example")):
                    continue

                if "noreply@" in lowered:
                    continue

                offenders.append(f"{os.path.relpath(path, REPO)}: {address}")

    assert not offenders, (
        f"addresses other than {SUPPORT_EMAIL} found: {offenders}"
    )


def test_no_support_at_style_address_was_invented():
    for _, route in EXPECTED:
        html = page_source(route).lower()

        for forbidden in ("support@", "help@", "info@", "contact@",
                          "admin@", "hello@"):
            assert forbidden not in html, (
                f"{route} invents a {forbidden}… address; only "
                f"{SUPPORT_EMAIL} is used"
            )


# =========================================================
# Content the product promises
# =========================================================

def test_no_page_offers_an_account_or_a_login():
    """
    V1 ships without authentication, so nothing may offer it.

    This looks for a real offer — a control, a field, a route — rather
    than for the words, because the pages legitimately use them to say
    that no account is needed.
    """

    for _, route in EXPECTED:
        html = page_source(route)

        assert not re.search(r'type="password"', html, re.I), (
            f"{route} has a password field"
        )

        for route_fragment in ('href="/login', 'href="/signup',
                               'href="/register', 'href="/account',
                               'href="/auth'):
            assert route_fragment not in html.lower(), (
                f"{route} links to authentication at {route_fragment}"
            )

        # No button or link whose own label offers an account.
        labels = re.findall(r">([^<>]{2,40})<", html)

        for label in labels:
            cleaned = " ".join(label.split()).lower().strip(" .,")

            assert cleaned not in ("sign up", "sign in", "log in",
                                   "login", "register", "create account",
                                   "my account"), (
                f"{route} offers {cleaned!r}, but V1 has no accounts"
            )


def test_the_policy_pages_say_what_they_must():
    """
    Each policy page has to actually cover its subject.

    A page that exists but says nothing useful is worse than none: it
    looks like the question was answered.
    """

    required = {
        "/privacy/": ["cookie", "third-party", "local storage",
                      "browser", "assistant"],
        "/terms/": ["acceptable use", "liability", "warranty",
                    "academic"],
        "/disclaimer/": ["verified", "not a substitute", "no warranty",
                         "language model"],
    }

    for route, phrases in required.items():
        text = page_text(route)

        for phrase in phrases:
            assert phrase in text, f"{route} never mentions {phrase!r}"


def test_the_privacy_page_is_honest_about_the_ai_provider():
    """
    Questions leave the service when the assistant is used.

    That is the single most important disclosure on the page, so it is
    pinned rather than left to survive an edit by luck.
    """

    text = page_text("/privacy/")

    assert "third-party" in text or "third party" in text
    assert "provider" in text
    assert "do not put anything confidential" in text


def test_the_disclaimer_is_linked_from_the_assistant_page():
    """Where generated text appears, the caveat must be one click away."""

    assert '/disclaimer/' in page_source("/assistant/")


def test_the_assistant_page_hosts_its_own_conversation():
    html = page_source("/assistant/")

    for element_id in ("chat-log", "chat-form", "chat-input", "chat-send"):
        assert f'id="{element_id}"' in html


def test_every_page_has_a_distinct_title_and_description():
    titles = {}
    descriptions = {}

    for _, route in EXPECTED:
        html = page_source(route)

        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
        description = re.search(
            r'<meta name="description" content="([^"]+)"', html
        ).group(1)

        assert "MathNova" in title, f"{route} title omits the product name"

        assert title not in titles, (
            f"{route} reuses the title of {titles.get(title)}"
        )
        assert description not in descriptions, (
            f"{route} reuses the description of {descriptions.get(description)}"
        )

        titles[title] = route
        descriptions[description] = route
