"""Tests for the VM."""

import pytest

from pvm.assembler import assemble
from pvm.errors import (
    CallDepthError,
    DivisionByZeroError,
    StackOverflowError,
    StackUnderflowError,
    StepLimitError,
    TypeMismatchError,
    UninitializedLocalError,
    VMError,
)
from pvm.vm import VM, VMConfig


def run_expression(instructions):
    output = []
    program = assemble(
        f"""
        func main 0 2
            {instructions}
            PRINT
            HALT
        """
    )
    VM(program, output=output.append).run()
    return output[0]


@pytest.mark.parametrize(
    ("instructions", "expected"),
    [
        ("LOAD_CONST 8\nLOAD_CONST 3\nADD", 11),
        ("LOAD_CONST 8\nLOAD_CONST 3\nSUB", 5),
        ("LOAD_CONST 8\nLOAD_CONST 3\nMUL", 24),
        ("LOAD_CONST -8\nLOAD_CONST 3\nDIV", -2),
        ("LOAD_CONST -8\nLOAD_CONST 3\nMOD", -2),
        ("LOAD_CONST 8\nNEG", -8),
        ("LOAD_CONST 2\nLOAD_CONST 3\nLT", True),
        ("LOAD_CONST 2\nLOAD_CONST 2\nEQ", True),
        ("LOAD_CONST 2\nLOAD_CONST 3\nNE", True),
        ("LOAD_CONST 2\nLOAD_CONST 2\nLE", True),
        ("LOAD_CONST 3\nLOAD_CONST 2\nGT", True),
        ("LOAD_CONST 3\nLOAD_CONST 3\nGE", True),
        ("LOAD_CONST true\nLOAD_CONST false\nAND", False),
        ("LOAD_CONST true\nLOAD_CONST false\nOR", True),
        ("LOAD_CONST true\nNOT", False),
    ],
)
def test_opcode_results(instructions, expected):
    assert run_expression(instructions) == expected


def test_stack_and_local_opcodes():
    assert (
        run_expression(
            """
            LOAD_CONST 9
            DUP
            STORE_VAR 0
            LOAD_CONST 2
            SWAP
            POP
            LOAD_VAR 0
            ADD
            """
        )
        == 11
    )


def test_return_from_main_yields_result():
    result = VM(assemble("func main 0 0\nLOAD_CONST 7\nRETURN")).run()
    assert result == 7


def test_call_passes_arguments_in_push_order():
    # The first value pushed becomes slot 0, the second becomes slot 1, so
    # sub2 computes slot0 - slot1 = 10 - 3 = 7.
    output = []
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST 10\n"
        "    LOAD_CONST 3\n"
        "    CALL sub2 2\n"
        "    PRINT\n"
        "    HALT\n"
        "func sub2 2 2\n"
        "    LOAD_VAR 0\n"
        "    LOAD_VAR 1\n"
        "    SUB\n"
        "    RETURN\n"
    )
    VM(program, output=output.append).run()
    assert output == [7]


def test_jump_if_true_executes_taken_branch():
    output = []
    program = assemble(
        """
        func main 0 0
            LOAD_CONST true
            JUMP_IF_TRUE taken
            LOAD_CONST 0
            PRINT
            HALT
        taken:
            LOAD_CONST 1
            PRINT
            HALT
        """
    )
    VM(program, output=output.append).run()
    assert output == [1]


def test_trace_contains_machine_state():
    traces = []
    VM(
        assemble("func main 0 0\nLOAD_CONST 1\nHALT"),
        trace=True,
        trace_output=traces.append,
        output=lambda _: None,
    ).run()
    assert "fn=main" in traces[0]
    assert "ip=0000" in traces[0]
    assert "op=LOAD_CONST" in traces[0]
    assert "stack=[1]" in traces[0]
    assert "depth=1" in traces[0]


def test_trace_defaults_to_stderr(capsys):
    VM(
        assemble("func main 0 0\nLOAD_CONST 1\nHALT"),
        trace=True,
        output=lambda _: None,
    ).run()
    captured = capsys.readouterr()
    assert "TRACE" in captured.err
    assert "TRACE" not in captured.out


def test_stack_underflow_is_clean():
    with pytest.raises(StackUnderflowError, match="function=main"):
        VM(assemble("func main 0 0\nPOP\nHALT")).run()


def test_division_by_zero_is_clean():
    with pytest.raises(DivisionByZeroError, match="division by zero"):
        run_expression("LOAD_CONST 1\nLOAD_CONST 0\nDIV")


def test_modulo_by_zero_is_clean():
    with pytest.raises(DivisionByZeroError, match="modulo by zero"):
        run_expression("LOAD_CONST 1\nLOAD_CONST 0\nMOD")


def test_call_with_insufficient_arguments_is_clean():
    program = assemble(
        "func main 0 0\n    CALL f 1\n    HALT\n"
        "func f 1 1\n    LOAD_VAR 0\n    RETURN\n"
    )
    with pytest.raises(StackUnderflowError, match="CALL needs 1"):
        VM(program).run()


def test_type_mismatch_is_clean():
    with pytest.raises(TypeMismatchError, match="expected integer"):
        run_expression("LOAD_CONST true\nLOAD_CONST 1\nADD")


def test_equality_compares_two_booleans():
    assert run_expression("LOAD_CONST true\nLOAD_CONST true\nEQ") is True
    assert run_expression("LOAD_CONST true\nLOAD_CONST false\nNE") is True


def test_equality_rejects_mixed_types():
    with pytest.raises(TypeMismatchError, match="cannot compare"):
        run_expression("LOAD_CONST 1\nLOAD_CONST true\nEQ")


def test_uninitialized_local_is_clean():
    with pytest.raises(UninitializedLocalError, match="uninitialized"):
        run_expression("LOAD_VAR 1")


def test_trace_reports_one_consistent_frame_across_call():
    traces = []
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST 5\n"
        "    CALL inc 1\n"
        "    PRINT\n"
        "    HALT\n"
        "func inc 1 1\n"
        "    LOAD_VAR 0\n"
        "    LOAD_CONST 1\n"
        "    ADD\n"
        "    RETURN\n"
    )
    VM(program, trace=True, trace_output=traces.append, output=lambda _: None).run()
    call_line = next(line for line in traces if "op=CALL" in line)
    # The CALL executes in main (no locals, depth 1); the trace shows main's
    # own frame, not the callee's freshly created one.
    assert "fn=main" in call_line
    assert "locals=[]" in call_line
    assert "depth=1" in call_line


def test_stack_limit():
    program = assemble("func main 0 0\nLOAD_CONST 1\nLOAD_CONST 2\nHALT")
    with pytest.raises(StackOverflowError, match="stack limit 1"):
        VM(program, config=VMConfig(max_stack_depth=1)).run()


def test_step_limit_stops_infinite_loops():
    # A tight loop grows neither the stack nor the call depth, so only the
    # step limit can stop it.
    program = assemble("func main 0 0\nloop:\n    JUMP loop\n")
    with pytest.raises(StepLimitError, match="step limit 1000"):
        VM(program, config=VMConfig(max_steps=1000)).run()


def test_nonpositive_limit_is_rejected():
    program = assemble("func main 0 0\nHALT")
    with pytest.raises(VMError, match="must be positive"):
        VM(program, config=VMConfig(max_stack_depth=0)).run()


def test_negative_max_steps_is_rejected():
    program = assemble("func main 0 0\nHALT")
    with pytest.raises(VMError, match="max_steps cannot be negative"):
        VM(program, config=VMConfig(max_steps=-1)).run()


def test_dup_underflow_is_clean():
    with pytest.raises(StackUnderflowError):
        VM(assemble("func main 0 0\nDUP\nHALT")).run()


def test_swap_underflow_is_clean():
    with pytest.raises(StackUnderflowError):
        VM(assemble("func main 0 0\nLOAD_CONST 1\nSWAP\nHALT")).run()


def test_jump_on_non_boolean_is_rejected():
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST 1\n"
        "    JUMP_IF_FALSE done\n"
        "done:\n"
        "    HALT\n"
    )
    with pytest.raises(TypeMismatchError, match="expected boolean"):
        VM(program).run()


def test_jump_if_true_on_non_boolean_is_rejected():
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST 1\n"
        "    JUMP_IF_TRUE done\n"
        "done:\n"
        "    HALT\n"
    )
    with pytest.raises(TypeMismatchError, match="expected boolean"):
        VM(program).run()


@pytest.mark.parametrize(
    ("instructions", "pattern"),
    [
        ("LOAD_CONST 1\nLOAD_CONST 2\nAND", "expected boolean"),
        ("LOAD_CONST 1\nLOAD_CONST 2\nOR", "expected boolean"),
        ("LOAD_CONST 1\nNOT", "expected boolean"),
    ],
)
def test_boolean_ops_reject_integers(instructions, pattern):
    with pytest.raises(TypeMismatchError, match=pattern):
        run_expression(instructions)


def test_halt_returns_stack_top_when_present():
    result = VM(assemble("func main 0 0\nLOAD_CONST 9\nHALT")).run()
    assert result == 9


def test_halt_returns_none_on_empty_stack():
    result = VM(assemble("func main 0 0\nHALT")).run()
    assert result is None


def test_call_depth_limit_is_enforced():
    program = assemble(
        "func main 0 0\nCALL a 0\nHALT\n"
        "func a 0 0\nCALL b 0\nRETURN\n"
        "func b 0 0\nRETURN\n"
    )
    with pytest.raises(CallDepthError, match="call depth limit"):
        VM(program, config=VMConfig(max_call_depth=2)).run()
