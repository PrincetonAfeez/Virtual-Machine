"""Readable assembly output for validated PVM programs."""

from __future__ import annotations

from .format import format_value
from .opcodes import OpCode, iter_instructions
from .program import Program
from .validate import validate_program


def disassemble(program: Program) -> str:
    """Render a validated Program back into readable assembly text.

    For assembler-produced programs the result reassembles to an equivalent
    Program. Only constants referenced by ``LOAD_CONST`` are emitted; unused
    pool entries from hand-built bytecode are omitted. Raises
    BytecodeValidationError if the program is invalid.
    """
    validate_program(program)
    function_names = program.function_names()
    output: list[str] = [f"; entrypoint {program.entrypoint}"]
    for function_number, function in enumerate(program.functions.values()):
        if function_number:
            output.append("")
        output.append(f"func {function.name} {function.arity} {function.num_locals}")
        instructions = iter_instructions(function.code)
        jump_targets = {
            operands[0]
            for _, opcode, operands, _ in instructions
            if opcode in (OpCode.JUMP, OpCode.JUMP_IF_FALSE, OpCode.JUMP_IF_TRUE)
        }
        labels = {target: f"L{target:04x}" for target in sorted(jump_targets)}

        for offset, opcode, operands, _ in instructions:
            if offset in labels:
                output.append(f"{labels[offset]}:")
            rendered: list[str] = []
            if opcode is OpCode.LOAD_CONST:
                rendered.append(format_value(program.constants[operands[0]]))
            elif opcode in (
                OpCode.JUMP,
                OpCode.JUMP_IF_FALSE,
                OpCode.JUMP_IF_TRUE,
            ):
                rendered.append(labels[operands[0]])
            elif opcode is OpCode.CALL:
                rendered.extend((function_names[operands[0]], str(operands[1])))
            else:
                rendered.extend(str(value) for value in operands)
            operand_text = (" " + " ".join(rendered)) if rendered else ""
            output.append(f"    {opcode.name}{operand_text}  ; @{offset:04x}")
    return "\n".join(output) + "\n"
