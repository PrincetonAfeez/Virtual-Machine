"""Two-pass assembler for PVM assembly source."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import AssemblerError, BytecodeValidationError
from .names import ENTRYPOINT_LINE, ENTRYPOINT_MALFORMED, is_valid_identifier
from .opcodes import SPECS, OpCode, encode_instruction
from .program import Function, Program
from .validate import validate_program

_I64_MIN = -(1 << 63)
_I64_MAX = (1 << 63) - 1
_LEADING_ZERO_DECIMAL = re.compile(r"^0[0-9]+$")


@dataclass(slots=True)
class _Instruction:
    mnemonic: str
    operands: list[str]
    line: int
    offset: int


@dataclass(slots=True)
class _FunctionIR:
    name: str
    arity: int
    num_locals: int
    line: int
    labels: dict[str, int] = field(default_factory=dict)
    instructions: list[_Instruction] = field(default_factory=list)
    code_size: int = 0


def _parse_int(token: str, line: int, description: str) -> int:
    try:
        return int(token, 0)
    except ValueError as exc:
        raise AssemblerError(f"invalid {description}: {token!r}", line) from exc


def _parse_non_negative_int(token: str, line: int, description: str) -> int:
    value = _parse_int(token, line, description)
    if value < 0:
        raise AssemblerError(f"{description} must be non-negative, got {value}", line)
    return value


def _strip_comment(line: str) -> str:
    positions = [
        position for marker in (";", "#", "//") if (position := line.find(marker)) >= 0
    ]
    return line[: min(positions)] if positions else line


def _instruction_from_tokens(
    tokens: list[str], line_number: int, offset: int
) -> _Instruction:
    mnemonic = tokens[0].upper()
    try:
        opcode = OpCode[mnemonic]
    except KeyError as exc:
        raise AssemblerError(f"unknown mnemonic {tokens[0]!r}", line_number) from exc
    expected = len(SPECS[opcode].operands)
    operands = tokens[1:]
    if len(operands) != expected:
        raise AssemblerError(
            f"{mnemonic} expects {expected} operand(s), got {len(operands)}",
            line_number,
        )
    return _Instruction(mnemonic, operands, line_number, offset)


def _pass_one(source: str) -> list[_FunctionIR]:
    functions: list[_FunctionIR] = []
    names: set[str] = set()
    current: _FunctionIR | None = None

    for line_number, raw_line in enumerate(source.splitlines(), 1):
        text = _strip_comment(raw_line).strip()
        if not text:
            continue
        tokens = text.replace(",", " ").split()
        if tokens[0].lower() == "func":
            if len(tokens) != 4:
                raise AssemblerError(
                    "function declaration must be: func <name> <arity> <num_locals>",
                    line_number,
                )
            name = tokens[1]
            if not is_valid_identifier(name):
                raise AssemblerError(f"invalid function name {name!r}", line_number)
            if name in names:
                raise AssemblerError(f"duplicate function {name!r}", line_number)
            arity = _parse_int(tokens[2], line_number, "function arity")
            num_locals = _parse_int(tokens[3], line_number, "local count")
            if not 0 <= arity <= 255 or not 0 <= num_locals <= 255:
                raise AssemblerError(
                    "arity and local count must be between 0 and 255",
                    line_number,
                )
            if num_locals < arity:
                raise AssemblerError(
                    "local count cannot be smaller than function arity",
                    line_number,
                )
            current = _FunctionIR(name, arity, num_locals, line_number)
            functions.append(current)
            names.add(name)
            continue
        if current is None:
            raise AssemblerError("instruction or label outside a function", line_number)

        if ":" in text:
            label_text, remainder = text.split(":", 1)
            label = label_text.strip()
            if not is_valid_identifier(label):
                raise AssemblerError(f"invalid label {label!r}", line_number)
            if label in current.labels:
                raise AssemblerError(f"duplicate label {label!r}", line_number)
            current.labels[label] = current.code_size
            text = remainder.strip()
            if not text:
                continue
            tokens = text.replace(",", " ").split()

        instruction = _instruction_from_tokens(tokens, line_number, current.code_size)
        current.instructions.append(instruction)
        opcode = OpCode[instruction.mnemonic]
        current.code_size += SPECS[opcode].size

    if not functions:
        raise AssemblerError("source contains no functions")
    if len(functions) > 65535:
        raise AssemblerError(
            "a program may define at most 65535 functions",
            functions[-1].line,
        )
    for function in functions:
        if not function.instructions:
            raise AssemblerError(
                f"function {function.name!r} contains no instructions", function.line
            )
        last = function.instructions[-1]
        if last.mnemonic not in ("HALT", "RETURN", "JUMP"):
            raise AssemblerError(
                f"function {function.name!r} must end with HALT, RETURN, or "
                f"JUMP, not {last.mnemonic}",
                last.line,
            )
    return functions


def _validate_i64_constant(value: int, line: int) -> int:
    if not _I64_MIN <= value <= _I64_MAX:
        raise AssemblerError(
            f"constant {value} does not fit in a signed 64-bit integer",
            line,
        )
    return value


def _entrypoint_from_source(source: str, default: str) -> tuple[str, int | None]:
    seen: str | None = None
    seen_line: int | None = None
    past_functions = False

    for line_number, line in enumerate(source.splitlines(), 1):
        text = _strip_comment(line).strip()
        if text.lower().startswith("func "):
            past_functions = True
            continue

        if ENTRYPOINT_MALFORMED.match(line):
            if past_functions:
                raise AssemblerError(
                    "entrypoint directive must appear before the first function",
                    line_number,
                )
            match = ENTRYPOINT_LINE.match(line)
            if match is None:
                raise AssemblerError(
                    "entrypoint directive requires a function name",
                    line_number,
                )
            name = match.group(1).strip()
            if not is_valid_identifier(name):
                raise AssemblerError(f"invalid entrypoint name {name!r}", line_number)
            if seen is not None:
                if seen == name:
                    raise AssemblerError(
                        f"duplicate entrypoint directive {name!r}",
                        line_number,
                    )
                raise AssemblerError(
                    f"conflicting entrypoint {name!r}; already set to {seen!r}",
                    line_number,
                )
            seen = name
            seen_line = line_number

    if seen is not None:
        return seen, seen_line
    return default, None


def _resolve_entrypoint(source: str, entrypoint: str | None) -> tuple[str, int | None]:
    if entrypoint is not None:
        if not is_valid_identifier(entrypoint):
            raise AssemblerError(f"invalid entrypoint name {entrypoint!r}", 1)
        return entrypoint, None
    return _entrypoint_from_source(source, "main")


def _validate_entrypoint(
    resolved_entrypoint: str,
    functions_ir: list[_FunctionIR],
    directive_line: int | None,
) -> None:
    function_indexes = {
        function.name: index for index, function in enumerate(functions_ir)
    }
    fallback_line = functions_ir[0].line if functions_ir else 1
    error_line = directive_line if directive_line is not None else fallback_line

    if resolved_entrypoint not in function_indexes:
        raise AssemblerError(
            f"entrypoint {resolved_entrypoint!r} does not exist; define the "
            f"function or pass entrypoint= to assemble()",
            error_line,
        )

    entry_ir = functions_ir[function_indexes[resolved_entrypoint]]
    if entry_ir.arity != 0:
        raise AssemblerError(
            f"entrypoint {resolved_entrypoint!r} must have arity 0, "
            f"got {entry_ir.arity}",
            entry_ir.line,
        )


def _constant_value(token: str, line: int) -> int | bool:
    lowered = token.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if _LEADING_ZERO_DECIMAL.match(token):
        raise AssemblerError(f"invalid constant: {token!r}", line)
    return _validate_i64_constant(_parse_int(token, line, "constant"), line)


def _constant_key(value: int | bool) -> tuple[type, int | bool]:
    return type(value), value


def assemble(source: str, *, entrypoint: str | None = None) -> Program:
    """Assemble assembly ``source`` into a validated Program.

    Raises AssemblerError (with a line number where applicable) on any
    syntactic or semantic error.
    """
    resolved_entrypoint, entrypoint_line = _resolve_entrypoint(source, entrypoint)
    functions_ir = _pass_one(source)
    _validate_entrypoint(resolved_entrypoint, functions_ir, entrypoint_line)
    function_indexes = {
        function.name: index for index, function in enumerate(functions_ir)
    }
    constants: list[int | bool] = []
    constant_indexes: dict[tuple[type, int | bool], int] = {}

    for function in functions_ir:
        for instruction in function.instructions:
            if instruction.mnemonic == "LOAD_CONST":
                value = _constant_value(instruction.operands[0], instruction.line)
                key = _constant_key(value)
                if key not in constant_indexes:
                    if len(constants) >= 65535:
                        raise AssemblerError("constant table is full", instruction.line)
                    constant_indexes[key] = len(constants)
                    constants.append(value)

    functions: dict[str, Function] = {}
    for function_ir in functions_ir:
        code = bytearray()
        for instruction in function_ir.instructions:
            opcode = OpCode[instruction.mnemonic]
            operands: tuple[int, ...]
            if opcode is OpCode.LOAD_CONST:
                value = _constant_value(instruction.operands[0], instruction.line)
                operands = (constant_indexes[_constant_key(value)],)
            elif opcode in (OpCode.LOAD_VAR, OpCode.STORE_VAR):
                slot = _parse_non_negative_int(
                    instruction.operands[0], instruction.line, "local slot"
                )
                if not 0 <= slot < function_ir.num_locals:
                    raise AssemblerError(
                        f"local slot {slot} is out of range for "
                        f"{function_ir.name!r}",
                        instruction.line,
                    )
                operands = (slot,)
            elif opcode in (
                OpCode.JUMP,
                OpCode.JUMP_IF_FALSE,
                OpCode.JUMP_IF_TRUE,
            ):
                target_token = instruction.operands[0]
                if target_token in function_ir.labels:
                    target = function_ir.labels[target_token]
                elif is_valid_identifier(target_token):
                    raise AssemblerError(
                        f"undefined label {target_token!r}", instruction.line
                    )
                else:
                    target = _parse_int(
                        target_token, instruction.line, "jump target or label"
                    )
                    if target < 0:
                        raise AssemblerError(
                            "jump target cannot be negative", instruction.line
                        )
                    # A numeric target must land on an instruction boundary;
                    # report it here with a line instead of deferring to the
                    # bytecode validator, which has no line information.
                    offsets = {item.offset for item in function_ir.instructions}
                    if target not in offsets:
                        raise AssemblerError(
                            f"jump target {target} is not an instruction " f"boundary",
                            instruction.line,
                        )
                operands = (target,)
            elif opcode is OpCode.CALL:
                target_name = instruction.operands[0]
                if target_name not in function_indexes:
                    raise AssemblerError(
                        f"undefined function {target_name!r}", instruction.line
                    )
                argc = _parse_non_negative_int(
                    instruction.operands[1], instruction.line, "argument count"
                )
                target_ir = functions_ir[function_indexes[target_name]]
                if argc != target_ir.arity:
                    raise AssemblerError(
                        f"{target_name} expects {target_ir.arity} "
                        f"argument(s), got {argc}",
                        instruction.line,
                    )
                operands = (function_indexes[target_name], argc)
            else:
                operands = ()
            try:
                code.extend(encode_instruction(opcode, operands))
            except ValueError as exc:
                raise AssemblerError(str(exc), instruction.line) from exc
        functions[function_ir.name] = Function(
            function_ir.name,
            function_ir.arity,
            function_ir.num_locals,
            bytes(code),
        )

    program = Program(constants, functions, resolved_entrypoint)
    # Re-run the shared validator so the assembler emits only programs the VM
    # will also accept; report any failure with assembler-style messaging.
    try:
        validate_program(program)
    except BytecodeValidationError as exc:
        fallback_line = functions_ir[0].line if functions_ir else 1
        raise AssemblerError(str(exc), fallback_line) from exc
    return program


def assemble_file(path: str, *, entrypoint: str | None = None) -> Program:
    """Read and assemble a UTF-8 assembly file into a validated Program.

    A leading byte-order mark is tolerated. Raises AssemblerError if the file
    cannot be read or assembled.
    """
    # "utf-8-sig" transparently strips a leading byte-order mark, which Windows
    # editors often add; plain "utf-8" would leave it on the first token.
    try:
        with open(path, encoding="utf-8-sig") as file:
            return assemble(file.read(), entrypoint=entrypoint)
    except UnicodeDecodeError as exc:
        raise AssemblerError(f"invalid UTF-8 in {path!r}") from exc
    except OSError as exc:
        raise AssemblerError(f"could not read {path!r}: {exc}") from exc
