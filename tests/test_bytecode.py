"""Tests for the bytecode module."""

import random

import pytest

from pvm.assembler import assemble
from pvm.bytecode import MAGIC, deserialize_program, serialize_program
from pvm.errors import BytecodeValidationError
from pvm.opcodes import OpCode, decode_instruction, encode_instruction
from pvm.program import Function, Program
from pvm.validate import validate_program

HALT = bytes([OpCode.HALT])


def sample_program():
    return assemble(
        """
        func main 0 0
            LOAD_CONST 42
            PRINT
            HALT
        """
    )


def test_serialization_round_trip():
    program = sample_program()
    assert deserialize_program(serialize_program(program)) == program


def test_serialization_round_trip_preserves_value_types_and_bounds():
    program = assemble(
        """
        func main 0 0
            LOAD_CONST true
            LOAD_CONST false
            LOAD_CONST -42
            LOAD_CONST 9223372036854775807
            LOAD_CONST -9223372036854775808
            HALT
        """
    )
    restored = deserialize_program(serialize_program(program))
    assert restored == program
    assert restored.constants == [
        True,
        False,
        -42,
        9223372036854775807,
        -9223372036854775808,
    ]
    assert [type(value) for value in restored.constants] == [
        bool,
        bool,
        int,
        int,
        int,
    ]


def test_file_header():
    payload = serialize_program(sample_program())
    assert payload.startswith(MAGIC + bytes([1]))


def test_bad_magic_is_rejected():
    payload = bytearray(serialize_program(sample_program()))
    payload[:4] = b"NOPE"
    with pytest.raises(BytecodeValidationError, match="magic"):
        deserialize_program(bytes(payload))


def test_version_mismatch_is_rejected():
    payload = bytearray(serialize_program(sample_program()))
    payload[4] = 99
    with pytest.raises(BytecodeValidationError, match="version 99"):
        deserialize_program(bytes(payload))


def test_truncated_bytecode_is_rejected():
    payload = serialize_program(sample_program())
    with pytest.raises(BytecodeValidationError, match="truncated"):
        deserialize_program(payload[:-1])


def test_unknown_opcode_is_rejected():
    program = Program([], {"main": Function("main", 0, 0, b"\xff")})
    with pytest.raises(BytecodeValidationError, match="unknown opcode"):
        validate_program(program)


def test_invalid_constant_index_is_rejected():
    code = encode_instruction(OpCode.LOAD_CONST, (2,)) + bytes([OpCode.HALT])
    program = Program([], {"main": Function("main", 0, 0, code)})
    with pytest.raises(BytecodeValidationError, match="constant index 2"):
        validate_program(program)


def test_invalid_jump_target_is_rejected():
    code = encode_instruction(OpCode.JUMP, (1,)) + bytes([OpCode.HALT])
    program = Program([], {"main": Function("main", 0, 0, code)})
    with pytest.raises(BytecodeValidationError, match="instruction boundary"):
        validate_program(program)


def test_missing_terminator_is_rejected():
    code = encode_instruction(OpCode.LOAD_CONST, (0,))
    program = Program([7], {"main": Function("main", 0, 0, code)})
    with pytest.raises(BytecodeValidationError, match="must end with"):
        validate_program(program)


def test_encode_instruction_validates_operands():
    with pytest.raises(ValueError, match="expects"):
        encode_instruction(OpCode.LOAD_CONST, ())
    with pytest.raises(ValueError, match="does not fit"):
        encode_instruction(OpCode.LOAD_VAR, (256,))


def test_decode_instruction_rejects_out_of_bounds_offset():
    with pytest.raises(BytecodeValidationError, match="out of bounds"):
        decode_instruction(b"", 0)


def test_deserialize_rejects_non_bytes():
    with pytest.raises(BytecodeValidationError, match="must be bytes"):
        deserialize_program("not bytes")


def _pack_text(value):
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(2, "big") + encoded


def test_duplicate_function_name_in_file_is_rejected():
    record = _pack_text("main") + bytes([0, 0]) + (1).to_bytes(4, "big") + HALT
    payload = (
        MAGIC
        + bytes([1])
        + _pack_text("main")
        + (0).to_bytes(2, "big")
        + (2).to_bytes(2, "big")
        + record
        + record
    )
    with pytest.raises(BytecodeValidationError, match="duplicate function"):
        deserialize_program(payload)


def test_truncated_operands_are_rejected():
    program = Program(
        [0], {"main": Function("main", 0, 0, bytes([OpCode.LOAD_CONST]))}, "main"
    )
    with pytest.raises(BytecodeValidationError, match="truncated"):
        validate_program(program)


def test_trailing_bytes_are_rejected():
    payload = serialize_program(sample_program()) + b"\x00"
    with pytest.raises(BytecodeValidationError, match="trailing"):
        deserialize_program(payload)


def test_unknown_constant_tag_is_rejected():
    # Layout: MAGIC(4) version(1) entrypoint("main": 2+4) count(2) -> tag at 13.
    payload = bytearray(serialize_program(sample_program()))
    assert payload[13] == 0  # int constant 42 carries type tag 0
    payload[13] = 5
    with pytest.raises(BytecodeValidationError, match="unknown constant type tag"):
        deserialize_program(bytes(payload))


def test_bad_boolean_constant_value_is_rejected():
    program = assemble("func main 0 0\nLOAD_CONST true\nHALT\n")
    payload = bytearray(serialize_program(program))
    assert payload[13] == 1  # bool constant carries type tag 1
    payload[14] = 2  # value byte must be 0 or 1
    with pytest.raises(BytecodeValidationError, match="boolean constant"):
        deserialize_program(bytes(payload))


def test_oversized_constant_table_is_rejected():
    program = Program([0] * 65536, {"main": Function("main", 0, 0, HALT)}, "main")
    with pytest.raises(BytecodeValidationError, match="too large"):
        serialize_program(program)


def test_long_text_field_is_rejected():
    name = "x" * 65536
    program = Program([], {name: Function(name, 0, 0, HALT)}, name)
    with pytest.raises(BytecodeValidationError, match="too long"):
        serialize_program(program)


def test_deserialize_only_raises_validation_errors_on_garbage():
    # Treat the loader as the trust boundary: no input, however malformed,
    # may escape as a raw exception; everything is a clean BytecodeValidationError.
    rng = random.Random(20240601)
    valid = serialize_program(sample_program())
    for _ in range(3000):
        if rng.random() < 0.4:
            data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 48)))
        else:
            buf = bytearray(valid)
            for _ in range(rng.randrange(1, 5)):
                buf[rng.randrange(len(buf))] = rng.randrange(256)
            if rng.random() < 0.25:
                buf = buf[: rng.randrange(len(buf) + 1)]
            data = bytes(buf)
        try:
            deserialize_program(data)
        except BytecodeValidationError:
            pass


def test_load_program_save_program_round_trip(tmp_path):
    from pvm.bytecode import load_program, save_program

    program = sample_program()
    path = tmp_path / "sample.bc"
    save_program(program, path)
    assert load_program(str(path)) == program


def test_custom_entrypoint_survives_serialization():
    program = assemble("func boot 0 0\nLOAD_CONST 1\nHALT", entrypoint="boot")
    restored = deserialize_program(serialize_program(program))
    assert restored.entrypoint == "boot"
    assert restored == program


def test_load_program_missing_file(tmp_path):
    from pvm.bytecode import load_program

    with pytest.raises(BytecodeValidationError, match="could not read"):
        load_program(str(tmp_path / "missing.bc"))


def test_save_program_unwritable_path(tmp_path):
    from pvm.bytecode import save_program

    program = sample_program()
    target = tmp_path / "missing" / "out.bc"
    with pytest.raises(BytecodeValidationError, match="could not write"):
        save_program(program, str(target))


def test_deserialize_rejects_invalid_utf8_entrypoint():
    payload = bytearray(serialize_program(sample_program()))
    # entrypoint text starts after MAGIC(4)+version(1); length at 5-6, bytes at 7+
    payload[7] = 0xFF
    with pytest.raises(BytecodeValidationError, match="UTF-8"):
        deserialize_program(bytes(payload))


def test_oversized_function_table_is_rejected():
    functions = {f"f{i}": Function(f"f{i}", 0, 0, HALT) for i in range(65536)}
    program = Program([], functions, "f0")
    with pytest.raises(BytecodeValidationError, match="too large"):
        serialize_program(program)
