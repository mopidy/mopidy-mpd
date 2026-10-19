import re
from pathlib import Path

import pytest
from mopidy.models import Track

from tests.protocol import BaseTestCase

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "tests/protocol/0.19"
BLOCK = re.compile(r"^```(mpd|expected)\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)


def steps(path):
    text = path.read_text(encoding="utf-8")
    blocks = list(BLOCK.finditer(text))
    if not blocks or len(blocks) % 2:
        raise ValueError(f"{path}: expected at least one mpd/expected pair")
    for command_block, expected_block in zip(blocks[::2], blocks[1::2], strict=True):
        if (
            command_block.group(1) != "mpd"
            or expected_block.group(1) != "expected"
            or text[command_block.end() : expected_block.start()].strip()
        ):
            raise ValueError(f"{path}: mpd must be immediately followed by expected")
        commands = command_block.group(2).splitlines()
        expected = expected_block.group(2).splitlines()
        if not commands or not expected:
            raise ValueError(f"{path}: empty commands or expectations")
        yield commands, expected


def matches(expected, actual):
    if expected.endswith(": *"):
        key = expected[:-1]
        return any(line.startswith(key) and line[len(key) :].strip() for line in actual)
    return expected in actual


@pytest.mark.parametrize(
    "scenario",
    [(path, list(steps(path))) for path in sorted(SCENARIOS.rglob("*.md"))],
    ids=lambda scenario: scenario[0].relative_to(ROOT).as_posix(),
)
def test_scenario(scenario):
    path, scenario_steps = scenario
    client = BaseTestCase()
    client.setUp()
    try:
        client.backend.library.dummy_library = [
            Track(uri="dummy:/a", name="A", length=40000),
            Track(uri="dummy:/b", name="B", length=50000),
        ]
        for number, (commands, expected) in enumerate(scenario_steps, start=1):
            actual = [
                line for command in commands for line in client.send_request(command)
            ]
            assert all(matches(line, actual) for line in expected), (
                f"{path.relative_to(ROOT)} step {number}\n"
                f"commands: {commands!r}\n"
                f"expected: {expected!r}\n"
                f"actual: {actual!r}"
            )
    finally:
        client.tearDown()
