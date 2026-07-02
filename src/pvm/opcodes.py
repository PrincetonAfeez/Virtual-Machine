"""Opcode definitions, operand layouts, and bytecode instruction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .errors import BytecodeValidationError


class OpCode(IntEnum):
    LOAD_CONST = 0x01
    POP = 0x02
    DUP = 0x03
    SWAP = 0x04

    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    MOD = 0x14
    NEG = 0x15

    EQ = 0x20
    NE = 0x21
    LT = 0x22
    LE = 0x23
    GT = 0x24
    GE = 0x25
    AND = 0x26
    OR = 0x27
    NOT = 0x28

    LOAD_VAR = 0x30
    STORE_VAR = 0x31

    JUMP = 0x40
    JUMP_IF_FALSE = 0x41
    JUMP_IF_TRUE = 0x42

    CALL = 0x50
    RETURN = 0x51

    PRINT = 0x60
    HALT = 0x61


@dataclass(frozen=True, slots=True)
class InstructionSpec:
    operands: tuple[int, ...]
    stack_effect: str

    @property
    def size(self) -> int:
        return 1 + sum(self.operands)


SPECS: dict[OpCode, InstructionSpec] = {
    OpCode.LOAD_CONST: InstructionSpec((2,), "[] -> [constant]"),
    OpCode.POP: InstructionSpec((), "[value] -> []"),
    OpCode.DUP: InstructionSpec((), "[value] -> [value, value]"),
    OpCode.SWAP: InstructionSpec((), "[left, right] -> [right, left]"),
    OpCode.ADD: InstructionSpec((), "[int, int] -> [int]"),
    OpCode.SUB: InstructionSpec((), "[int, int] -> [int]"),
    OpCode.MUL: InstructionSpec((), "[int, int] -> [int]"),
    OpCode.DIV: InstructionSpec((), "[int, int] -> [int]"),
    OpCode.MOD: InstructionSpec((), "[int, int] -> [int]"),
    OpCode.NEG: InstructionSpec((), "[int] -> [int]"),
    OpCode.EQ: InstructionSpec((), "[T, T] -> [bool]"),
    OpCode.NE: InstructionSpec((), "[T, T] -> [bool]"),
    OpCode.LT: InstructionSpec((), "[int, int] -> [bool]"),
    OpCode.LE: InstructionSpec((), "[int, int] -> [bool]"),
    OpCode.GT: InstructionSpec((), "[int, int] -> [bool]"),
    OpCode.GE: InstructionSpec((), "[int, int] -> [bool]"),
    OpCode.AND: InstructionSpec((), "[bool, bool] -> [bool]"),
    OpCode.OR: InstructionSpec((), "[bool, bool] -> [bool]"),
    OpCode.NOT: InstructionSpec((), "[bool] -> [bool]"),
    OpCode.LOAD_VAR: InstructionSpec((1,), "[] -> [local]"),
    OpCode.STORE_VAR: InstructionSpec((1,), "[value] -> []"),
    OpCode.JUMP: InstructionSpec((2,), "[] -> []"),
    OpCode.JUMP_IF_FALSE: InstructionSpec((2,), "[bool] -> []"),
    OpCode.JUMP_IF_TRUE: InstructionSpec((2,), "[bool] -> []"),
    OpCode.CALL: InstructionSpec((2, 1), "[arg1, ...] -> [result]"),
    OpCode.RETURN: InstructionSpec((), "[result] -> caller"),
    OpCode.PRINT: InstructionSpec((), "[value] -> []"),
    OpCode.HALT: InstructionSpec((), "halt"),
}


def encode_instruction(opcode: OpCode, operands: tuple[int, ...] = ()) -> bytes:
    """Encode an opcode and its operands into bytes.

    Raises ValueError if the operand count is wrong or a value does not fit
    in its declared width.
    """
    widths = SPECS[opcode].operands
    if len(widths) != len(operands):
        raise ValueError(f"{opcode.name} expects {len(widths)} operand(s)")
    result = bytearray([opcode])
    for value, width in zip(operands, widths, strict=True):
        if value < 0 or value >= 1 << (width * 8):
            raise ValueError(f"operand {value} does not fit in {width} byte(s)")
        result.extend(value.to_bytes(width, "big"))
    return bytes(result)


def decode_instruction(code: bytes, ip: int) -> tuple[OpCode, tuple[int, ...], int]:
    """Decode the instruction at ``ip`` as ``(opcode, operands, size)``.

    Raises BytecodeValidationError if the offset is out of range, the opcode
    is unknown, or the operands are truncated.
    """
    if ip < 0 or ip >= len(code):
        raise BytecodeValidationError(f"instruction offset {ip} is out of bounds")
    raw_opcode = code[ip]
    try:
        opcode = OpCode(raw_opcode)
    except ValueError as exc:
        raise BytecodeValidationError(
            f"unknown opcode 0x{raw_opcode:02x} at offset {ip}"
        ) from exc
    spec = SPECS[opcode]
    end = ip + spec.size
    if end > len(code):
        raise BytecodeValidationError(
            f"truncated operands for {opcode.name} at offset {ip}"
        )
    cursor = ip + 1
    operands: list[int] = []
    for width in spec.operands:
        operands.append(int.from_bytes(code[cursor : cursor + width], "big"))
        cursor += width
    return opcode, tuple(operands), spec.size


def iter_instructions(
    code: bytes,
) -> list[tuple[int, OpCode, tuple[int, ...], int]]:
    instructions: list[tuple[int, OpCode, tuple[int, ...], int]] = []
    ip = 0
    while ip < len(code):
        opcode, operands, size = decode_instruction(code, ip)
        instructions.append((ip, opcode, operands, size))
        ip += size
    return instructions
