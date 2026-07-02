"""Tests for the assembler internals."""

import pytest

from pvm.assembler import assemble, assemble_file
from pvm.errors import AssemblerError


def test_hash_comments_strip_before_parsing():
    program = assemble("func main 0 0\n# LOAD_CONST 99\nLOAD_CONST 1\nHALT\n")
    assert program.constants == [1]


def test_double_slash_comments_strip_before_parsing():
    program = assemble("func main 0 0\n// comment\nLOAD_CONST 2\nHALT\n")
    assert program.constants == [2]


def test_commas_separate_operands():
    program = assemble("func main 0 0\nCALL helper, 0\nHALT\nfunc helper 0 0\nRETURN\n")
    assert "helper" in program.functions


def test_undefined_identifier_jump_target_is_rejected():
    with pytest.raises(AssemblerError, match="undefined label"):
        assemble("func main 0 0\nJUMP missing_label\nHALT\n")


def test_function_may_end_with_unconditional_jump():
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST 1\n"
        "    JUMP done\n"
        "    LOAD_CONST 0\n"
        "done:\n"
        "    HALT\n"
    )
    assert program.functions["main"].code


def test_assemble_file_reads_from_disk(tmp_path):
    path = tmp_path / "p.asm"
    path.write_text("func main 0 0\nLOAD_CONST 4\nHALT\n", encoding="utf-8")
    program = assemble_file(str(path))
    assert program.constants == [4]


def test_negative_function_arity_is_rejected():
    with pytest.raises(AssemblerError, match="between 0 and 255"):
        assemble("func main -1 0\nHALT\n")
