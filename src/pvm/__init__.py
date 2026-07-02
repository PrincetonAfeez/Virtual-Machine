"""Python stack-based virtual machine."""

from .assembler import assemble, assemble_file
from .bytecode import (
    deserialize_program,
    load_program,
    save_program,
    serialize_program,
)
from .disassembler import disassemble
from .errors import (
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
from .format import format_value
from .program import Function, Program
from .validate import validate_program
from .vm import VM, VMConfig

__all__ = [
    "AssemblerError",
    "BytecodeValidationError",
    "CallDepthError",
    "DivisionByZeroError",
    "Function",
    "InvalidCallError",
    "InvalidJumpError",
    "PVMError",
    "Program",
    "StackOverflowError",
    "StackUnderflowError",
    "StepLimitError",
    "TypeMismatchError",
    "UninitializedLocalError",
    "VM",
    "VMConfig",
    "VMError",
    "assemble",
    "assemble_file",
    "deserialize_program",
    "disassemble",
    "format_value",
    "load_program",
    "save_program",
    "serialize_program",
    "validate_program",
    "__version__",
]

__version__ = "1.0.5"
