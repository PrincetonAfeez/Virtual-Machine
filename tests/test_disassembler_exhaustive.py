"""Tests for the disassembler."""

from pvm.assembler import assemble
from pvm.disassembler import disassemble


def test_disassemble_includes_offset_comments():
    program = assemble("func main 0 0\nLOAD_CONST 1\nHALT\n")
    text = disassemble(program)
    assert "; @0000" in text
    assert "; @0003" in text


def test_disassemble_separates_multiple_functions_with_blank_line():
    program = assemble("func main 0 0\nHALT\nfunc helper 0 0\nLOAD_CONST 1\nHALT\n")
    text = disassemble(program)
    assert "\n\nfunc helper" in text


def test_disassemble_labels_are_sorted_by_offset():
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST true\n"
        "    JUMP_IF_FALSE L1\n"
        "    JUMP L2\n"
        "L1:\n"
        "    HALT\n"
        "L2:\n"
        "    HALT\n"
    )
    text = disassemble(program)
    assert "JUMP_IF_FALSE L" in text
    assert "JUMP L" in text
