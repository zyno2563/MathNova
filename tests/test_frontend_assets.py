"""
Static guards on the frontend assets.

These are deliberately narrow. Each one encodes a bug that actually
shipped and was not caught by asserting on the DOM — the elements were
present and correctly positioned, but something painted on top of them.
"""

import glob
import os
import re

FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend"
)


def read(*parts):
    with open(os.path.join(FRONTEND, *parts), encoding="utf-8") as handle:
        return handle.read()


def page_files():
    """Every page of the site, as (route, absolute path)."""

    found = []

    for path in sorted(glob.glob(os.path.join(FRONTEND, "**", "index.html"),
                                 recursive=True)):
        route = os.path.relpath(path, FRONTEND)[: -len("index.html")]
        found.append(("/" + route.replace(os.sep, "/"), path))

    return found


def page_sources():
    """The markup of every page, keyed by route."""

    return {
        route: open(path, encoding="utf-8").read()
        for route, path in page_files()
    }


def test_referenced_assets_exist():
    """Every local css/js file any page points at must be present."""

    pages = page_sources()

    assert pages, "no pages found"

    for route, html in pages.items():
        references = re.findall(r'(?:src|href)="(/(?:js|css)/[^"]+)"', html)

        assert references, f"{route} references no local assets"

        for reference in references:
            path = os.path.join(FRONTEND, reference.lstrip("/"))
            assert os.path.isfile(path), f"{route}: missing asset {reference}"


def test_chat_message_classes_are_namespaced():
    """
    A chat message must never take the bare role as a class name.

    `class="msg assistant"` collided with the panel's own `.assistant`
    rule, which made every assistant message `position: fixed` and
    full height — covering the close button and the input box.
    """

    source = read("js", "assistant.js")

    assert "msg--" in source, "message role classes must use the msg-- prefix"

    forbidden = re.search(r"`msg \$\{\s*role\s*\}`", source)
    assert forbidden is None, (
        "message class interpolates the bare role; it must be "
        "`msg--${role}` so it cannot collide with component classes"
    )


def test_component_classes_do_not_collide_with_message_modifiers():
    """
    No component rule may match a chat message's own classes.

    The message element carries `msg` plus `msg--<role>`; a top-level
    rule for either name would style every message.
    """

    css = read("css", "styles.css")

    selectors = set(re.findall(r"^\s*(\.[a-z][\w-]*)\s*[,{]", css, re.MULTILINE))

    for role in ("user", "assistant"):
        assert f".{role}" not in selectors, (
            f"'.{role}' is a top-level CSS class and would style chat "
            f"messages carrying that role"
        )


def test_hidden_attribute_is_enforced_over_component_display():
    """
    Components that set `display` would otherwise ignore `hidden`.

    The assistant panel is `display: flex`, which outranks the user
    agent's `[hidden] { display: none }` and left the panel open on
    first paint.
    """

    css = read("css", "styles.css")

    assert re.search(r"\[hidden\]\s*\{[^}]*display:\s*none\s*!important", css), (
        "styles.css must restate [hidden] { display: none !important } "
        "because components set display explicitly"
    )


def test_elements_the_scripts_drive_exist_somewhere_in_the_markup():
    """
    Every getElementById the site boots with must resolve.

    Part of the chrome is injected at runtime by shell.js rather than
    written into each page, so the ids it creates count as defined —
    which is why its own template is scanned alongside the pages.
    """

    ids = set()

    for _, html in page_sources().items():
        ids.update(re.findall(r'id="([^"]+)"', html))

    # Ids created by the shared chrome.
    for source_name in ("shell.js",):
        ids.update(re.findall(r'id="([^"]+)"', read("js", source_name)))

    for source_name in ("app.js", "assistant.js", "shell.js", "page.js"):
        source = read("js", source_name)

        for element_id in re.findall(
            r"getElementById\(['\"]([^'\"]+)['\"]\)", source
        ):
            assert element_id in ids, (
                f"{source_name} looks up #{element_id}, which no page "
                f"and no injected template defines"
            )


def test_the_ui_names_no_ai_vendor():
    """
    Which model answers is a server-side configuration detail.

    The panel used to hardcode one vendor's name and one vendor's
    environment variable, so swapping providers meant editing the
    frontend. Everything user-visible now comes from
    /api/assistant/status.
    """

    for route, html in page_sources().items():
        assert not re.search(r"anthropic|\bclaude\b|gemini|groq|ollama", html, re.I), (
            f"{route} names an AI vendor; the UI must stay provider-neutral"
        )

    for source_name in ("assistant.js", "shell.js", "page.js"):
        source = read("js", source_name)

        assert not re.search(
            r"anthropic|\bclaude\b|gemini|groq|ollama", source, re.I
        ), (
            f"{source_name} names an AI vendor or an API key variable; the "
            f"provider name must come from /api/assistant/status"
        )


def test_the_panel_never_reveals_which_backend_answers():
    """
    The interface must not name the provider or the model.

    It used to greet with "Running on <provider> (<model>)", which told
    every visitor which vendor the deployment used. The server no longer
    reports either, and no page may reintroduce them.
    """

    for source_name in ("assistant.js", "page.js", "shell.js"):
        source = read("js", source_name)

        for field in ("provider_label", "status.provider", "status.model",
                      "setup_hint"):
            assert field not in source, (
                f"{source_name} reads {field}, which the status endpoint "
                f"deliberately no longer returns"
            )


def test_the_panel_renders_what_the_server_does_report():
    """An unavailable assistant still has to say so."""

    source = read("js", "assistant.js")

    assert "/api/assistant/status" in source
    assert "status.enabled" in source
    assert "status.message" in source, (
        "the panel must render the server's message when the assistant "
        "is unavailable"
    )


def test_fourier_results_are_not_captioned_in_laplace_notation():
    """
    Several transforms return the same keys with different meanings.

    A transform's input is always `f` and its output is always `F`, but
    Laplace writes those f(t) and F(s) while Fourier writes f(x) and
    F(omega). The shared label map is Laplace's, so the Fourier methods
    must override it — otherwise a Fourier result is captioned "F(s)"
    beside an expression in omega.
    """

    source = read("js", "modules.js")

    # The generic renderer has to accept an override at all.
    assert "renderGeneric(result, labels" in source or \
           "labels = null" in source, (
        "renderGeneric takes no label override"
    )

    fourier = re.findall(
        r"endpoint: '/api/transforms/fourier[^']*',(.{0,400}?)fields:",
        source, re.S
    )

    assert len(fourier) == 2, (
        f"expected 2 Fourier methods, found {len(fourier)}"
    )

    for block in fourier:
        assert "labels:" in block, (
            "a Fourier method does not override the Laplace labels"
        )
        assert "f(x)" in block and "F(\u03c9)" in block or "F(ω)" in block, (
            "the Fourier override does not use Fourier notation"
        )


def test_the_app_passes_label_overrides_to_the_renderer():
    """An override nothing forwards would be silently dead."""

    source = read("js", "app.js")

    assert "renderGeneric(result, method.labels)" in source, (
        "app.js calls renderGeneric without the method's label overrides"
    )


def test_a_markdown_rule_is_not_rendered_as_dashes():
    """
    Models separate sections with `---`.

    Rendered literally it looks like a glitch mid-answer, which is how
    it appeared in the Android app.
    """

    source = read("js", "assistant.js")

    assert "/^-{3,}$/" in source, "a line of dashes must become a divider"
    assert "<hr" in source


def test_wide_equations_can_be_reached_on_a_phone():
    """
    A displayed equation is often wider than a phone screen.

    Without its own scroll it is clipped at the bubble's edge with no
    way to see the rest.
    """

    css = read("css", "styles.css")

    block = re.search(
        r"\.msg \.bubble \.katex-display \{[^}]*\}", css
    )

    assert block, "chat bubbles do not give displayed equations a scroll"
    assert "overflow-x: auto" in block.group(0)
