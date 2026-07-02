"""Public error hierarchy for PVM."""

from __future__ import annotations


class PVMError(Exception):
    """Base class for expected, user-facing PVM failures."""


class AssemblerError(PVMError):
    """Assembly source is invalid."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        prefix = f"line {line}: " if line is not None else ""
        super().__init__(prefix + message)


class BytecodeValidationError(PVMError):
    """A program or serialized bytecode file is malformed."""


class VMError(PVMError):
    """Base class for execution failures with machine context."""

    def __init__(
        self,
        message: str,
        *,
        function: str | None = None,
        ip: int | None = None,
        opcode: str | None = None,
    ) -> None:
        self.function = function
        self.ip = ip
        self.opcode = opcode
        context: list[str] = []
        if function is not None:
            context.append(f"function={function}")
        if ip is not None:
            context.append(f"ip={ip}")
        if opcode is not None:
            context.append(f"opcode={opcode}")
        suffix = f" ({', '.join(context)})" if context else ""
        super().__init__(message + suffix)


class StackUnderflowError(VMError):
    """An instruction tried to pop a missing operand."""


class StackOverflowError(VMError):
    """The configured operand-stack limit was exceeded."""


class CallDepthError(VMError):
    """The configured call-depth limit was exceeded."""


class StepLimitError(VMError):
    """The configured instruction-step limit was exceeded."""


class InvalidJumpError(VMError):
    """A jump target is invalid."""


class DivisionByZeroError(VMError):
    """Integer division or modulo by zero was attempted."""


class TypeMismatchError(VMError):
    """An instruction received operands of the wrong runtime type."""


class InvalidCallError(VMError):
    """A function call is invalid."""


class UninitializedLocalError(VMError):
    """A local slot was read before it was written."""
