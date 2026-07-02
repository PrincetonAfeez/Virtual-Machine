"""Tests for the bytecode reader."""

import pytest

from pvm.assembler import assemble
from pvm.bytecode import deserialize_program, serialize_program
from pvm.errors import BytecodeValidationError
from pvm.program import Function


def test_function_dataclass_stores_fields():
    function = Function("main", 2, 4, b"\x61")
    assert function.name == "main"
    assert function.arity == 2
    assert function.num_locals == 4
    assert function.code == b"\x61"


def test_program_equality_compares_all_fields():
    left = assemble("func main 0 0\nLOAD_CONST 1\nHALT\n")
    right = assemble("func main 0 0\nLOAD_CONST 1\nHALT\n")
    assert left == right


def test_deserialize_reports_truncation_at_constant_count():
    payload = b"PVM1\x01" + (4).to_bytes(2, "big") + b"main" + (1).to_bytes(2, "big")
    with pytest.raises(BytecodeValidationError, match="truncated"):
        deserialize_program(payload)


def test_deserialize_reports_truncation_at_function_name():
    program = assemble("func main 0 0\nHALT\n")
    payload = bytearray(serialize_program(program))
    # Chop off tail of first function record to force truncation mid-name.
    del payload[-2:]
    with pytest.raises(BytecodeValidationError, match="truncated"):
        deserialize_program(bytes(payload))


def test_deserialize_reports_invalid_utf8_function_name():
    program = assemble("func main 0 0\nHALT\n")
    payload = bytearray(serialize_program(program))
    # Function name text begins after constants section; corrupt first name byte.
    payload[17] = 0xFF
    with pytest.raises(BytecodeValidationError, match="UTF-8"):
        deserialize_program(bytes(payload))
