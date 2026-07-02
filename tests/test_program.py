"""Tests for the program module."""

import pytest

from pvm.program import Function, Program


def test_program_defaults():
    program = Program()
    assert program.constants == []
    assert program.functions == {}
    assert program.entrypoint == "main"


def test_function_names_preserves_insertion_order():
    program = Program(
        [],
        {
            "main": Function("main", 0, 0, b""),
            "helper": Function("helper", 0, 0, b""),
        },
    )
    assert program.function_names() == ["main", "helper"]


def test_function_by_index_returns_matching_function():
    helper = Function("helper", 1, 1, b"")
    program = Program([], {"main": Function("main", 0, 0, b""), "helper": helper})
    assert program.function_by_index(1) is helper


def test_function_by_index_out_of_range():
    program = Program([], {"main": Function("main", 0, 0, b"")})
    with pytest.raises(IndexError):
        program.function_by_index(1)
