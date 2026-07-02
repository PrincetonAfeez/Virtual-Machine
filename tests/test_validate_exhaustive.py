"""Tests for the validate module."""

import pytest

from pvm.errors import BytecodeValidationError
from pvm.opcodes import OpCode, encode_instruction
from pvm.program import Function, Program
from pvm.validate import validate_program

HALT = bytes([OpCode.HALT])


def test_jump_if_false_invalid_target_is_rejected():
    code = encode_instruction(OpCode.JUMP_IF_FALSE, (1,)) + HALT
    program = Program([], {"main": Function("main", 0, 0, code)})
    with pytest.raises(BytecodeValidationError, match="instruction boundary"):
        validate_program(program)


def test_function_must_not_fall_off_end_with_non_transfer_opcode():
    code = encode_instruction(OpCode.LOAD_CONST, (0,))
    program = Program([0], {"main": Function("main", 0, 0, code)})
    with pytest.raises(BytecodeValidationError, match="must end with"):
        validate_program(program)


def test_validate_program_accepts_valid_minimal_program():
    validate_program(Program([], {"main": Function("main", 0, 0, HALT)}))
