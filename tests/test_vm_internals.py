"""Tests for the VM internals."""

import pytest

from pvm.assembler import assemble
from pvm.errors import (
    StackUnderflowError,
    TypeMismatchError,
    VMError,
)
from pvm.vm import VM, VMConfig


def test_default_output_writes_to_stdout(capsys):
    VM(assemble("func main 0 0\nLOAD_CONST 1\nPRINT\nHALT")).run()
    assert capsys.readouterr().out == "1\n"


def test_default_trace_writes_to_stderr(capsys):
    VM(assemble("func main 0 0\nLOAD_CONST 1\nHALT"), trace=True).run()
    assert "TRACE" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (7, 3, 2),
        (-7, 3, -2),
        (7, -3, -2),
        (-7, -3, 2),
        (1, 2, 0),
    ],
)
def test_trunc_div_matches_expected_sign_rules(left, right, expected):
    assert VM._trunc_div(left, right) == expected


def test_vm_config_defaults():
    config = VMConfig()
    assert config.max_stack_depth == 1024
    assert config.max_call_depth == 256
    assert config.max_steps == 10_000_000


def test_jump_if_false_falls_through_when_condition_true():
    output = []
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST true\n"
        "    JUMP_IF_FALSE skip\n"
        "    LOAD_CONST 5\n"
        "    PRINT\n"
        "skip:\n"
        "    HALT\n"
    )
    VM(program, output=output.append).run()
    assert output == [5]


def test_unconditional_jump_skips_intermediate_code():
    output = []
    program = assemble(
        "func main 0 0\n"
        "    JUMP target\n"
        "    LOAD_CONST 0\n"
        "    PRINT\n"
        "target:\n"
        "    LOAD_CONST 3\n"
        "    PRINT\n"
        "    HALT\n"
    )
    VM(program, output=output.append).run()
    assert output == [3]


def test_return_from_nested_call_restores_caller_stack():
    output = []
    program = assemble(
        "func main 0 0\n"
        "    CALL inner 0\n"
        "    PRINT\n"
        "    HALT\n"
        "func inner 0 0\n"
        "    LOAD_CONST 4\n"
        "    RETURN\n"
    )
    VM(program, output=output.append).run()
    assert output == [4]


def test_pop_two_underflow_via_binary_int_op():
    with pytest.raises(StackUnderflowError, match="two values"):
        VM(assemble("func main 0 0\nLOAD_CONST 1\nADD\nHALT")).run()


def test_neg_requires_integer():
    with pytest.raises(TypeMismatchError, match="expected integer"):
        VM(assemble("func main 0 0\nLOAD_CONST true\nNEG\nHALT")).run()


def test_integer_compare_requires_integer():
    with pytest.raises(TypeMismatchError, match="expected integer"):
        VM(assemble("func main 0 0\n" "LOAD_CONST true\nLOAD_CONST 1\nLT\nHALT")).run()


def test_nonpositive_call_depth_is_rejected():
    with pytest.raises(VMError, match="must be positive"):
        VM(
            assemble("func main 0 0\nHALT"),
            config=VMConfig(max_call_depth=0),
        ).run()


def test_vm_error_includes_opcode_name_on_failure():
    with pytest.raises(StackUnderflowError) as excinfo:
        VM(assemble("func main 0 0\nPOP\nHALT")).run()
    assert excinfo.value.opcode == "POP"
    assert excinfo.value.function == "main"


def test_trace_renders_dash_for_operandless_ops():
    traces = []
    VM(
        assemble("func main 0 0\nHALT"),
        trace=True,
        trace_output=traces.append,
        output=lambda _: None,
    ).run()
    assert "args=-" in traces[0]
    assert "op=HALT" in traces[0]
