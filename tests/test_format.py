"""Tests for the format module."""

import pytest

from pvm.format import format_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, "true"),
        (False, "false"),
        (0, "0"),
        (-1, "-1"),
        (9223372036854775807, "9223372036854775807"),
    ],
)
def test_format_value_renders_vm_types(value, expected):
    assert format_value(value) == expected


def test_format_value_rejects_non_vm_types():
    with pytest.raises(TypeError, match="cannot format"):
        format_value(None)
    with pytest.raises(TypeError, match="cannot format"):
        format_value("hello")
    with pytest.raises(TypeError, match="cannot format"):
        format_value(1.5)
