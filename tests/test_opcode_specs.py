"""Tests for the opcode specs."""

import pytest

from pvm.opcodes import SPECS, InstructionSpec, OpCode, encode_instruction


@pytest.mark.parametrize("opcode", list(OpCode))
def test_every_opcode_has_instruction_spec(opcode):
    spec = SPECS[opcode]
    assert isinstance(spec, InstructionSpec)
    assert spec.size == 1 + sum(spec.operands)
    assert spec.stack_effect


@pytest.mark.parametrize("opcode", list(OpCode))
def test_spec_size_matches_encoded_length(opcode):
    widths = SPECS[opcode].operands
    operands = tuple(0 for _ in widths)
    if opcode is OpCode.LOAD_CONST:
        operands = (0,)
    elif opcode is OpCode.CALL:
        operands = (0, 0)
    assert len(encode_instruction(opcode, operands)) == SPECS[opcode].size


def test_opcode_values_are_unique():
    values = [opcode.value for opcode in OpCode]
    assert len(values) == len(set(values))
