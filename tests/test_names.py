"""Tests for the names module."""

import re

import pytest

from pvm.names import ENTRYPOINT_LINE, ENTRYPOINT_MALFORMED, is_valid_identifier


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("main", True),
        ("_boot", True),
        ("CamelCase42", True),
        ("", False),
        ("9bad", False),
        ("bad-name", False),
        ("caf\u00e9", False),
        ("a", True),
    ],
)
def test_is_valid_identifier(name, expected):
    assert is_valid_identifier(name) is expected


def test_entrypoint_malformed_matches_comment_prefixes():
    assert ENTRYPOINT_MALFORMED.match("; entrypoint")
    assert ENTRYPOINT_MALFORMED.match("# entrypoint boot")
    assert ENTRYPOINT_MALFORMED.match("  // entrypoint")
    assert ENTRYPOINT_MALFORMED.match("  ; entrypoint boot") is not None
    assert ENTRYPOINT_MALFORMED.match("func main") is None


def test_entrypoint_line_extracts_name():
    match = ENTRYPOINT_LINE.match("; entrypoint boot")
    assert match is not None
    assert match.group(1).strip() == "boot"
    match = ENTRYPOINT_LINE.match("# entrypoint main")
    assert match is not None
    assert match.group(1).strip() == "main"
    assert ENTRYPOINT_LINE.match("; entrypoint") is None


def test_identifier_pattern_matches_names_module_export():
    assert re.fullmatch(r"^[A-Za-z_][A-Za-z0-9_]*$", "main")
