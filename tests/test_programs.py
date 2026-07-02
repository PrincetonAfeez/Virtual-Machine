"""Tests for the programs module."""

from pathlib import Path

import pytest

from pvm.assembler import assemble_file
from pvm.errors import (
    AssemblerError,
    CallDepthError,
    DivisionByZeroError,
    StackUnderflowError,
)
from pvm.vm import VM, VMConfig

EXAMPLES = Path(__file__).parents[1] / "examples"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("arithmetic.asm", [14]),
        ("if_else.asm", [100]),
        ("loop.asm", [15]),
        ("factorial.asm", [120]),
        ("fibonacci.asm", [55]),
    ],
)
def test_example_programs(name, expected):
    output = []
    VM(assemble_file(str(EXAMPLES / name)), output=output.append).run()
    assert output == expected


def test_factorial_uses_vm_frames():
    vm = VM(assemble_file(str(EXAMPLES / "factorial.asm")), output=lambda _: None)
    vm.run()
    assert vm.max_call_depth_seen == 6


@pytest.mark.parametrize(
    ("name", "error"),
    [
        ("bad_stack_underflow.asm", StackUnderflowError),
        ("bad_div_zero.asm", DivisionByZeroError),
    ],
)
def test_runtime_failure_examples_raise_clean_errors(name, error):
    with pytest.raises(error):
        VM(assemble_file(str(EXAMPLES / name)), output=lambda _: None).run()


def test_bad_jump_example_is_rejected_when_assembled():
    # This example fails static validation, so it never produces bytecode.
    with pytest.raises(AssemblerError, match="instruction boundary"):
        assemble_file(str(EXAMPLES / "bad_jump.asm"))


def test_infinite_recursion_hits_vm_limit():
    source = """
    func main 0 0
        CALL forever 0
        HALT
    func forever 0 0
        CALL forever 0
        RETURN
    """
    with pytest.raises(CallDepthError, match="call depth limit"):
        VM(assemble_file_from_text(source), config=VMConfig(max_call_depth=8)).run()


def assemble_file_from_text(source):
    from pvm.assembler import assemble

    return assemble(source)
