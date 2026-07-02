"""Tests for the disassembler."""

import pytest

from pvm.assembler import assemble
from pvm.disassembler import disassemble
from pvm.errors import BytecodeValidationError
from pvm.program import Function, Program


def test_disassemble_rejects_invalid_program():
    program = Program([], {"main": Function("main", 0, 0, b"\xff")}, "main")
    with pytest.raises(BytecodeValidationError, match="unknown opcode"):
        disassemble(program)


def test_disassemble_from_asm_via_cli_path(tmp_path):
    source = tmp_path / "boot.asm"
    source.write_text("func boot 0 0\nLOAD_CONST 3\nHALT\n", encoding="utf-8")
    from pvm.assembler import assemble_file

    text = disassemble(assemble_file(str(source), entrypoint="boot"))
    assert text.startswith("; entrypoint boot\n")
    assert "LOAD_CONST 3" in text


def test_disassemble_renders_call_with_function_name():
    program = assemble("func main 0 0\nCALL helper 0\nHALT\nfunc helper 0 0\nRETURN\n")
    text = disassemble(program)
    assert "CALL helper 0" in text
