"""Serialization for the PVM1 bytecode file format."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import BytecodeValidationError
from .program import Function, Program
from .validate import validate_program

MAGIC = b"PVM1"
VERSION = 1


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _encode_text(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) > 65535:
        raise BytecodeValidationError("text field is too long")
    return _u16(len(encoded)) + encoded


def serialize_program(program: Program) -> bytes:
    """Serialize a validated Program to a PVM1 bytecode payload.

    Raises BytecodeValidationError if the program is invalid or its tables are
    too large to encode.
    """
    validate_program(program)
    if len(program.constants) > 65535 or len(program.functions) > 65535:
        raise BytecodeValidationError("program table is too large")

    data = bytearray(MAGIC)
    data.append(VERSION)
    data.extend(_encode_text(program.entrypoint))
    data.extend(_u16(len(program.constants)))
    for value in program.constants:
        if type(value) is bool:
            data.extend((1, int(value)))
        else:
            data.append(0)
            data.extend(value.to_bytes(8, "big", signed=True))

    data.extend(_u16(len(program.functions)))
    for function in program.functions.values():
        data.extend(_encode_text(function.name))
        data.extend((function.arity, function.num_locals))
        data.extend(len(function.code).to_bytes(4, "big"))
        data.extend(function.code)
    return bytes(data)


@dataclass(slots=True)
class _Reader:
    data: bytes
    cursor: int = 0

    def read(self, count: int, description: str) -> bytes:
        end = self.cursor + count
        if end > len(self.data):
            raise BytecodeValidationError(
                f"truncated bytecode while reading {description}"
            )
        chunk = self.data[self.cursor : end]
        self.cursor = end
        return chunk

    def u8(self, description: str) -> int:
        return self.read(1, description)[0]

    def u16(self, description: str) -> int:
        return int.from_bytes(self.read(2, description), "big")

    def u32(self, description: str) -> int:
        return int.from_bytes(self.read(4, description), "big")

    def text(self, description: str) -> str:
        length = self.u16(f"{description} length")
        raw = self.read(length, description)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BytecodeValidationError(f"{description} is not valid UTF-8") from exc


def deserialize_program(data: bytes) -> Program:
    """Parse a PVM1 bytecode payload into a validated Program.

    Raises BytecodeValidationError on malformed magic/version data,
    truncation, trailing bytes, or any invalid structure.
    """
    if not isinstance(data, bytes):
        raise BytecodeValidationError("bytecode input must be bytes")
    reader = _Reader(data)
    if reader.read(4, "magic bytes") != MAGIC:
        raise BytecodeValidationError("invalid bytecode magic; expected PVM1")
    version = reader.u8("version")
    if version != VERSION:
        raise BytecodeValidationError(
            f"unsupported bytecode version {version}; expected {VERSION}"
        )
    entrypoint = reader.text("entrypoint")

    constants: list[int | bool] = []
    for index in range(reader.u16("constant count")):
        tag = reader.u8(f"constant {index} type")
        if tag == 0:
            constants.append(
                int.from_bytes(
                    reader.read(8, f"constant {index} value"),
                    "big",
                    signed=True,
                )
            )
        elif tag == 1:
            value = reader.u8(f"constant {index} value")
            if value not in (0, 1):
                raise BytecodeValidationError(
                    f"boolean constant {index} must be 0 or 1"
                )
            constants.append(bool(value))
        else:
            raise BytecodeValidationError(
                f"unknown constant type tag {tag} at index {index}"
            )

    functions: dict[str, Function] = {}
    function_count = reader.u16("function count")
    for index in range(function_count):
        name = reader.text(f"function {index} name")
        if name in functions:
            raise BytecodeValidationError(f"duplicate function name {name!r}")
        arity = reader.u8(f"function {name!r} arity")
        num_locals = reader.u8(f"function {name!r} local count")
        code_length = reader.u32(f"function {name!r} code length")
        code = reader.read(code_length, f"function {name!r} code")
        functions[name] = Function(name, arity, num_locals, code)

    if reader.cursor != len(data):
        raise BytecodeValidationError(
            f"unexpected {len(data) - reader.cursor} trailing byte(s)"
        )
    program = Program(constants, functions, entrypoint)
    # A well-formed file can still describe a semantically invalid program, so
    # validate the decoded structure before handing it back to a caller.
    validate_program(program)
    return program


def load_program(path: str) -> Program:
    """Load and validate a PVM1 bytecode file.

    Raises BytecodeValidationError if the file cannot be read or is invalid.
    """
    try:
        with open(path, "rb") as file:
            return deserialize_program(file.read())
    except OSError as exc:
        raise BytecodeValidationError(f"could not read {path!r}: {exc}") from exc


def save_program(program: Program, path: str) -> None:
    """Serialize ``program`` and write the PVM1 payload to ``path``.

    Raises BytecodeValidationError if serialization or writing fails.
    """
    payload = serialize_program(program)
    try:
        with open(path, "wb") as file:
            file.write(payload)
    except OSError as exc:
        raise BytecodeValidationError(f"could not write {path!r}: {exc}") from exc
