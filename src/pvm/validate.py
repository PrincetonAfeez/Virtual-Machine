"""Defensive validation for untrusted in-memory programs."""

from __future__ import annotations

from .errors import BytecodeValidationError
from .names import is_valid_identifier
from .opcodes import OpCode, iter_instructions
from .program import Program


def validate_program(program: Program) -> None:
    """Defensively validate an in-memory Program before execution.

    Treats the program as untrusted input and raises BytecodeValidationError
    on the first structural or semantic problem found.
    """
    if not isinstance(program, Program):
        raise BytecodeValidationError("loaded object is not a Program")
    if not program.functions:
        raise BytecodeValidationError("program has no functions")
    if program.entrypoint not in program.functions:
        raise BytecodeValidationError(
            f"entrypoint {program.entrypoint!r} does not exist"
        )
    if not is_valid_identifier(program.entrypoint):
        raise BytecodeValidationError(
            f"entrypoint {program.entrypoint!r} is not a valid identifier"
        )

    for index, value in enumerate(program.constants):
        if type(value) not in (int, bool):
            raise BytecodeValidationError(
                f"constant {index} has unsupported type {type(value).__name__}"
            )
        if type(value) is int and not -(1 << 63) <= value < (1 << 63):
            raise BytecodeValidationError(
                f"constant {index} does not fit in a signed 64-bit integer"
            )

    function_names = program.function_names()

    for table_name, function in program.functions.items():
        if not table_name or function.name != table_name:
            raise BytecodeValidationError(
                f"function table key {table_name!r} does not match function name"
            )
        if not is_valid_identifier(function.name):
            raise BytecodeValidationError(
                f"function {table_name!r} has an invalid name; only ASCII "
                f"identifiers matching [A-Za-z_][A-Za-z0-9_]* are accepted"
            )
        if not 0 <= function.arity <= 255:
            raise BytecodeValidationError(
                f"function {table_name!r} has invalid arity {function.arity}"
            )
        if not 0 <= function.num_locals <= 255:
            raise BytecodeValidationError(
                f"function {table_name!r} has invalid local count"
            )
        if function.num_locals < function.arity:
            raise BytecodeValidationError(
                f"function {table_name!r} has fewer locals than arguments"
            )
        if not isinstance(function.code, bytes) or not function.code:
            raise BytecodeValidationError(
                f"function {table_name!r} must contain bytecode"
            )

        try:
            instructions = iter_instructions(function.code)
        except BytecodeValidationError as exc:
            raise BytecodeValidationError(f"in function {table_name!r}: {exc}") from exc
        boundaries = {offset for offset, _, _, _ in instructions}

        for offset, opcode, operands, _ in instructions:
            if opcode is OpCode.LOAD_CONST:
                index = operands[0]
                if index >= len(program.constants):
                    raise BytecodeValidationError(
                        f"in function {table_name!r} at {offset}: "
                        f"constant index {index} is out of range"
                    )
            elif opcode in (OpCode.LOAD_VAR, OpCode.STORE_VAR):
                slot = operands[0]
                if slot >= function.num_locals:
                    raise BytecodeValidationError(
                        f"in function {table_name!r} at {offset}: "
                        f"local slot {slot} is out of range"
                    )
            elif opcode in (
                OpCode.JUMP,
                OpCode.JUMP_IF_FALSE,
                OpCode.JUMP_IF_TRUE,
            ):
                target = operands[0]
                if target not in boundaries:
                    raise BytecodeValidationError(
                        f"in function {table_name!r} at {offset}: "
                        f"jump target {target} is not an instruction boundary"
                    )
            elif opcode is OpCode.CALL:
                target_index, argc = operands
                if target_index >= len(function_names):
                    raise BytecodeValidationError(
                        f"in function {table_name!r} at {offset}: "
                        f"function index {target_index} is out of range"
                    )
                callee = program.functions[function_names[target_index]]
                if argc != callee.arity:
                    raise BytecodeValidationError(
                        f"in function {table_name!r} at {offset}: "
                        f"{callee.name} expects {callee.arity} argument(s), got {argc}"
                    )

        # Control must not be able to fall off the end of the code: the final
        # instruction has to transfer control unconditionally.
        last_opcode = instructions[-1][1]
        if last_opcode not in (OpCode.HALT, OpCode.RETURN, OpCode.JUMP):
            raise BytecodeValidationError(
                f"function {table_name!r} must end with HALT, RETURN, or JUMP, "
                f"not {last_opcode.name}"
            )

    entry = program.functions[program.entrypoint]
    if entry.arity != 0:
        raise BytecodeValidationError("entrypoint must have arity 0")
