"""Tests for the error hierarchy."""

import pytest

from pvm.errors import (
    AssemblerError,
    BytecodeValidationError,
    CallDepthError,
    DivisionByZeroError,
    InvalidCallError,
    InvalidJumpError,
    PVMError,
    StackOverflowError,
    StackUnderflowError,
    StepLimitError,
    TypeMismatchError,
    UninitializedLocalError,
    VMError,
)


@pytest.mark.parametrize(
    "cls",
    [
        AssemblerError,
        BytecodeValidationError,
        VMError,
        StackUnderflowError,
        StackOverflowError,
        CallDepthError,
        StepLimitError,
        InvalidJumpError,
        DivisionByZeroError,
        TypeMismatchError,
        InvalidCallError,
        UninitializedLocalError,
    ],
)
def test_error_classes_inherit_from_pvm_error(cls):
    assert issubclass(cls, PVMError)


@pytest.mark.parametrize(
    "cls",
    [
        StackUnderflowError,
        StackOverflowError,
        CallDepthError,
        StepLimitError,
        InvalidJumpError,
        DivisionByZeroError,
        TypeMismatchError,
        InvalidCallError,
        UninitializedLocalError,
    ],
)
def test_runtime_errors_inherit_from_vm_error(cls):
    assert issubclass(cls, VMError)


def test_vm_error_without_context():
    error = VMError("plain failure")
    assert str(error) == "plain failure"
    assert error.function is None
    assert error.ip is None
    assert error.opcode is None


def test_assembler_error_stores_line():
    error = AssemblerError("syntax", 3)
    assert error.line == 3


@pytest.mark.parametrize(
    "cls",
    [
        CallDepthError,
        DivisionByZeroError,
        InvalidCallError,
        InvalidJumpError,
        StackOverflowError,
        StackUnderflowError,
        StepLimitError,
        TypeMismatchError,
        UninitializedLocalError,
    ],
)
def test_vm_error_subclasses_accept_context(cls):
    error = cls("failure", function="main", ip=0, opcode="HALT")
    assert "function=main" in str(error)
