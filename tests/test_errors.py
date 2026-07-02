"""Tests for the errors."""

from pvm.errors import (
    AssemblerError,
    BytecodeValidationError,
    InvalidJumpError,
    PVMError,
    StackUnderflowError,
    VMError,
)


def test_assembler_error_includes_line_prefix():
    error = AssemblerError("bad token", 12)
    assert error.line == 12
    assert str(error) == "line 12: bad token"


def test_assembler_error_without_line_omits_prefix():
    error = AssemblerError("no functions")
    assert error.line is None
    assert str(error) == "no functions"


def test_vm_error_includes_execution_context():
    error = StackUnderflowError(
        "operand stack underflow",
        function="main",
        ip=4,
        opcode="POP",
    )
    assert error.function == "main"
    assert error.ip == 4
    assert error.opcode == "POP"
    assert "function=main" in str(error)
    assert "ip=4" in str(error)
    assert "opcode=POP" in str(error)


def test_invalid_jump_error_is_a_vm_error():
    error = InvalidJumpError("jump target 1 is not an instruction boundary")
    assert isinstance(error, VMError)
    assert isinstance(error, PVMError)


def test_bytecode_validation_error_is_a_pvm_error():
    assert issubclass(BytecodeValidationError, PVMError)
