"""Tests for the validate module."""

import pytest

from pvm.errors import BytecodeValidationError
from pvm.opcodes import OpCode, encode_instruction
from pvm.program import Function, Program
from pvm.validate import validate_program

HALT = bytes([OpCode.HALT])


def _program(constants=(), functions=None, entrypoint="main"):
    if functions is None:
        functions = {"main": Function("main", 0, 0, HALT)}
    return Program(list(constants), functions, entrypoint)


def test_non_program_is_rejected():
    with pytest.raises(BytecodeValidationError, match="not a Program"):
        validate_program("not a program")


def test_empty_program_is_rejected():
    with pytest.raises(BytecodeValidationError, match="no functions"):
        validate_program(Program([], {}, "main"))


def test_missing_entrypoint_is_rejected():
    functions = {"other": Function("other", 0, 0, HALT)}
    with pytest.raises(BytecodeValidationError, match="entrypoint 'main'"):
        validate_program(Program([], functions, "main"))


def test_unsupported_constant_type_is_rejected():
    with pytest.raises(BytecodeValidationError, match="unsupported type str"):
        validate_program(_program(constants=["x"]))


def test_out_of_range_constant_is_rejected():
    with pytest.raises(BytecodeValidationError, match="64-bit"):
        validate_program(_program(constants=[1 << 63]))


def test_function_table_key_mismatch_is_rejected():
    functions = {"main": Function("other", 0, 0, HALT)}
    with pytest.raises(BytecodeValidationError, match="does not match"):
        validate_program(Program([], functions, "main"))


def test_invalid_arity_is_rejected():
    functions = {"main": Function("main", 300, 300, HALT)}
    with pytest.raises(BytecodeValidationError, match="invalid arity"):
        validate_program(Program([], functions, "main"))


def test_invalid_local_count_is_rejected():
    functions = {"main": Function("main", 0, 300, HALT)}
    with pytest.raises(BytecodeValidationError, match="invalid local count"):
        validate_program(Program([], functions, "main"))


def test_fewer_locals_than_arity_is_rejected():
    functions = {
        "main": Function("main", 0, 0, HALT),
        "f": Function("f", 2, 1, HALT),
    }
    with pytest.raises(BytecodeValidationError, match="fewer locals"):
        validate_program(Program([], functions, "main"))


def test_empty_code_is_rejected():
    functions = {"main": Function("main", 0, 0, b"")}
    with pytest.raises(BytecodeValidationError, match="must contain bytecode"):
        validate_program(Program([], functions, "main"))


def test_local_slot_out_of_range_is_rejected():
    code = encode_instruction(OpCode.LOAD_VAR, (3,)) + HALT
    functions = {"main": Function("main", 0, 1, code)}
    with pytest.raises(BytecodeValidationError, match="local slot 3"):
        validate_program(Program([], functions, "main"))


def test_call_index_out_of_range_is_rejected():
    code = encode_instruction(OpCode.CALL, (5, 0)) + HALT
    functions = {"main": Function("main", 0, 0, code)}
    with pytest.raises(BytecodeValidationError, match="function index 5"):
        validate_program(Program([], functions, "main"))


def test_call_arity_mismatch_is_rejected():
    code = encode_instruction(OpCode.CALL, (1, 2)) + HALT
    functions = {
        "main": Function("main", 0, 0, code),
        "f": Function("f", 1, 1, HALT),
    }
    with pytest.raises(BytecodeValidationError, match="expects 1 argument"):
        validate_program(Program([], functions, "main"))


def test_entrypoint_must_have_arity_zero():
    functions = {"main": Function("main", 1, 1, HALT)}
    with pytest.raises(BytecodeValidationError, match="arity 0"):
        validate_program(Program([], functions, "main"))


def test_invalid_function_name_is_rejected():
    functions = {
        "main": Function("main", 0, 0, HALT),
        "caf\u00e9": Function("caf\u00e9", 0, 0, HALT),
    }
    with pytest.raises(BytecodeValidationError, match="invalid name"):
        validate_program(Program([], functions, "main"))


def test_store_var_out_of_range_is_rejected():
    code = encode_instruction(OpCode.STORE_VAR, (3,)) + HALT
    functions = {"main": Function("main", 0, 1, code)}
    with pytest.raises(BytecodeValidationError, match="local slot 3"):
        validate_program(Program([], functions, "main"))


def test_jump_if_true_invalid_target_is_rejected():
    code = encode_instruction(OpCode.JUMP_IF_TRUE, (1,)) + HALT
    program = Program([], {"main": Function("main", 0, 0, code)})
    with pytest.raises(BytecodeValidationError, match="instruction boundary"):
        validate_program(program)


def test_invalid_entrypoint_name_is_rejected():
    functions = {"bad-name": Function("bad-name", 0, 0, HALT)}
    with pytest.raises(BytecodeValidationError, match="not a valid identifier"):
        validate_program(Program([], functions, "bad-name"))


def test_validate_wraps_decode_errors_with_function_name():
    program = Program([], {"main": Function("main", 0, 0, b"\xff")}, "main")
    with pytest.raises(BytecodeValidationError, match="in function 'main'"):
        validate_program(program)
