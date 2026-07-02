"""Tests for the opcodes module."""

import pytest

from pvm.errors import BytecodeValidationError
from pvm.opcodes import (
    SPECS,
    OpCode,
    decode_instruction,
    encode_instruction,
    iter_instructions,
)


def test_every_opcode_has_a_spec():
    for opcode in OpCode:
        assert opcode in SPECS
        assert SPECS[opcode].size >= 1


@pytest.mark.parametrize("opcode", list(OpCode))
def test_encode_decode_round_trip(opcode):
    widths = SPECS[opcode].operands
    operands = tuple(0 for _ in widths)
    if opcode is OpCode.LOAD_CONST:
        operands = (0,)
    elif opcode is OpCode.CALL:
        operands = (0, 0)
    code = encode_instruction(opcode, operands)
    decoded_opcode, decoded_operands, size = decode_instruction(code, 0)
    assert decoded_opcode is opcode
    assert decoded_operands == operands
    assert size == len(code)


def test_iter_instructions_walks_entire_function():
    code = (
        encode_instruction(OpCode.LOAD_CONST, (0,))
        + encode_instruction(OpCode.PRINT, ())
        + bytes([OpCode.HALT])
    )
    instructions = iter_instructions(code)
    assert [item[1] for item in instructions] == [
        OpCode.LOAD_CONST,
        OpCode.PRINT,
        OpCode.HALT,
    ]
    assert [item[0] for item in instructions] == [0, 3, 4]


def test_encode_instruction_rejects_unknown_operand_count():
    with pytest.raises(ValueError, match="expects 1 operand"):
        encode_instruction(OpCode.JUMP, ())


def test_encode_instruction_rejects_oversized_u8_operand():
    with pytest.raises(ValueError, match="does not fit"):
        encode_instruction(OpCode.LOAD_VAR, (256,))


def test_decode_instruction_rejects_negative_offset():
    with pytest.raises(BytecodeValidationError, match="out of bounds"):
        decode_instruction(bytes([OpCode.HALT]), -1)


def test_decode_instruction_rejects_truncated_operands():
    code = bytes([OpCode.LOAD_CONST, 0])
    with pytest.raises(BytecodeValidationError, match="truncated operands"):
        decode_instruction(code, 0)
