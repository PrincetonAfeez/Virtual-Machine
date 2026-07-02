"""Execute every VM opcode handler at least once."""

import pytest

from pvm.assembler import assemble
from pvm.opcodes import OpCode
from pvm.vm import VM

# Minimal sources that retire each opcode exactly once before HALT/RETURN.
_OPCODE_SOURCES: dict[OpCode, str] = {
    OpCode.LOAD_CONST: "LOAD_CONST 1",
    OpCode.POP: "LOAD_CONST 1\nPOP",
    OpCode.DUP: "LOAD_CONST 1\nDUP\nPOP",
    OpCode.SWAP: "LOAD_CONST 1\nLOAD_CONST 2\nSWAP",
    OpCode.ADD: "LOAD_CONST 1\nLOAD_CONST 2\nADD",
    OpCode.SUB: "LOAD_CONST 5\nLOAD_CONST 2\nSUB",
    OpCode.MUL: "LOAD_CONST 3\nLOAD_CONST 4\nMUL",
    OpCode.DIV: "LOAD_CONST 8\nLOAD_CONST 2\nDIV",
    OpCode.MOD: "LOAD_CONST 8\nLOAD_CONST 3\nMOD",
    OpCode.NEG: "LOAD_CONST 4\nNEG",
    OpCode.EQ: "LOAD_CONST 1\nLOAD_CONST 1\nEQ",
    OpCode.NE: "LOAD_CONST 1\nLOAD_CONST 2\nNE",
    OpCode.LT: "LOAD_CONST 1\nLOAD_CONST 2\nLT",
    OpCode.LE: "LOAD_CONST 1\nLOAD_CONST 1\nLE",
    OpCode.GT: "LOAD_CONST 2\nLOAD_CONST 1\nGT",
    OpCode.GE: "LOAD_CONST 2\nLOAD_CONST 2\nGE",
    OpCode.AND: "LOAD_CONST true\nLOAD_CONST false\nAND",
    OpCode.OR: "LOAD_CONST true\nLOAD_CONST false\nOR",
    OpCode.NOT: "LOAD_CONST true\nNOT",
    OpCode.LOAD_VAR: "LOAD_CONST 7\nSTORE_VAR 0\nLOAD_VAR 0",
    OpCode.STORE_VAR: "LOAD_CONST 7\nSTORE_VAR 0",
    OpCode.JUMP: "JUMP target\nLOAD_CONST 0\ntarget:\nLOAD_CONST 1",
    OpCode.JUMP_IF_FALSE: (
        "LOAD_CONST false\nJUMP_IF_FALSE taken\nLOAD_CONST 0\n" "taken:\nLOAD_CONST 1"
    ),
    OpCode.JUMP_IF_TRUE: (
        "LOAD_CONST true\nJUMP_IF_TRUE taken\nLOAD_CONST 0\n" "taken:\nLOAD_CONST 1"
    ),
    OpCode.CALL: "CALL helper 0",
    OpCode.RETURN: "LOAD_CONST 9\nRETURN",
    OpCode.PRINT: "LOAD_CONST 1\nPRINT",
    OpCode.HALT: "LOAD_CONST 0",
}


def _program_for_opcode(opcode: OpCode) -> str:
    body = _OPCODE_SOURCES[opcode]
    if opcode is OpCode.CALL:
        return (
            f"func main 0 0\n    {body}\n    HALT\n"
            "func helper 0 0\n    LOAD_CONST 1\n    RETURN\n"
        )
    if opcode is OpCode.RETURN:
        return f"func main 0 0\n    {body}\n"
    return f"func main 0 2\n    {body}\n    HALT\n"


@pytest.mark.parametrize("opcode", list(OpCode))
def test_vm_executes_every_opcode_handler(opcode):
    program = assemble(_program_for_opcode(opcode))
    output = []
    vm = VM(program, output=output.append)
    vm.run()
    assert vm.opcode_counts[opcode] >= 1


def test_vm_handler_map_covers_all_opcodes():
    vm = VM(assemble("func main 0 0\nHALT\n"))
    assert set(vm._handlers) == set(OpCode)
