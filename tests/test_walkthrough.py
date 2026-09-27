"""
Worked examples and step-by-step solutions.

"Load example" used to reload the values the form already showed, so it
did exactly what Compute did and looked broken. And a result was a flat
list of equations with no account of how it was reached. These guard
both: that every method has more than one example to move between, and
that every method explains its working.
"""

import os
import re

FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)


def read(*parts):
    with open(os.path.join(FRONTEND, *parts), encoding="utf-8") as handle:
        return handle.read()


def entries():
    """Each walkthrough key with the source block that follows it."""

    source = read("js", "walkthrough.js")

    keys = list(re.finditer(r"^  '([a-z-]+:[a-z-]+)': \{", source, re.M))

    found = {}

    for index, match in enumerate(keys):
        end = keys[index + 1].start() if index + 1 < len(keys) else len(source)
        found[match.group(1)] = source[match.start():end]

    return found


def method_ids():
    """
    Every module:method pair the solver actually offers.

    Anchored on the markers that only one kind of block has — `glyph:`
    for a module, `endpoint:` for a method — and matched to the nearest
    id above. Reading ids in order instead mistook a method for a module
    whenever the next module began within a few lines.
    """

    source = read("js", "modules.js")

    ids = [(m.start(), m.group(1)) for m in re.finditer(r"id: '([a-z-]+)'", source)]

    def nearest_id_above(position):
        found = [name for start, name in ids if start < position]
        return found[-1] if found else None

    modules = {}

    for match in re.finditer(r"\bglyph: '", source):
        modules[match.start()] = nearest_id_above(match.start())

    pairs = []

    for match in re.finditer(r"\bendpoint: '", source):
        method = nearest_id_above(match.start())
        owning = [name for start, name in modules.items() if start < match.start()]

        if method and owning:
            pairs.append(f"{owning[-1]}:{method}")

    return pairs


def test_every_method_has_a_walkthrough():
    missing = [pair for pair in method_ids() if pair not in entries()]

    assert not missing, f"methods with no worked example or steps: {missing}"


def test_no_walkthrough_points_at_a_method_that_does_not_exist():
    offered = set(method_ids())

    stray = [key for key in entries() if key not in offered]

    assert not stray, f"walkthrough entries for unknown methods: {stray}"


def test_every_method_offers_more_than_one_example():
    """
    The form opens on the first example.

    With only one, pressing "Load example" reloads what is already on
    screen and is indistinguishable from Compute — the bug this fixes.
    """

    thin = {}

    for key, block in entries().items():
        count = len(re.findall(r"\{ label: ['\"]", block))

        if count < 2:
            thin[key] = count

    assert not thin, f"methods with fewer than two examples: {thin}"


def test_every_example_is_labelled():
    """The note tells the reader which example they are looking at."""

    for key, block in entries().items():
        labels = [text for _, text in re.findall(r"label: (['\"])(.*?)\1", block)]

        assert labels, f"{key} has no labelled examples"

        for label in labels:
            assert label.strip(), f"{key} has a blank example label"


def test_every_method_explains_its_working():
    for key, block in entries().items():
        titles = re.findall(r"title: '", block)
        explains = re.findall(r"explain: '", block)

        assert len(titles) >= 2, f"{key} has fewer than two steps"
        assert len(explains) >= len(titles) - 1, (
            f"{key} has steps with no explanation"
        )


def test_steps_are_built_from_engine_fields():
    """
    The working shown must be the engine's own.

    Every step names result fields; prose alone would be a second,
    unverified derivation sitting next to the verified one.
    """

    for key, block in entries().items():
        assert "keys: [" in block, f"{key} has steps that name no fields"


def test_the_example_button_moves_through_the_examples():
    source = read("js", "app.js")

    assert "function loadExample()" in source
    assert "exampleIndex" in source, "the button must remember its position"
    assert "walkthroughFor(" in source

    # The old behaviour — reload the defaults and recompute — was the bug.
    assert not re.search(
        r"dom\.example\.addEventListener\('click', \(\) => \{\s*"
        r"state\.values = defaultValues", source
    ), "the example button still just restores the defaults"


def test_the_page_can_say_which_example_is_loaded():
    assert 'id="example-note"' in read("solver", "index.html")
    assert "dom.exampleNote" in read("js", "app.js")


def test_the_renderer_can_lay_a_result_out_as_steps():
    modules = read("js", "modules.js")

    assert "export function renderSteps" in modules
    assert "renderGeneric(result, labels = null, steps = null)" in modules, (
        "renderGeneric must accept steps so the worked solution replaces "
        "the flat list instead of repeating it"
    )

    assert re.search(r"\.steps \{[^}]*counter-reset: step", read("css", "pages.css")), (
        "steps are not numbered in the stylesheet"
    )
