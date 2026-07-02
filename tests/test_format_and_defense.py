"""Tests for the format and defense modules."""


import pytest

from pvm.assembler import assemble
from pvm.errors import InvalidCallError, InvalidJumpError, VMError
from pvm.format import format_value
from pvm.opcodes import OpCode, encode_instruction
from pvm.program import Function, Program
from pvm.vm import VM


def test_format_value_renders_booleans_in_lowercase():
    assert format_value(True) == "true"
    assert format_value(False) == "false"
    assert format_value(42) == "42"


def test_format_value_rejects_non_vm_types():
    with pytest.raises(TypeError, match="cannot format"):
        format_value(None)


def test_vm_output_can_use_format_value():
    output = []
    program = assemble("func main 0 0\nLOAD_CONST true\nPRINT\nHALT")
    VM(program, output=lambda value: output.append(format_value(value))).run()
    assert output == ["true"]


def test_runtime_invalid_jump_with_validation_disabled(monkeypatch):
    code = encode_instruction(OpCode.JUMP, (1,)) + bytes([OpCode.HALT])
    program = Program([], {"main": Function("main", 0, 0, code)})
    monkeypatch.setattr("pvm.vm.validate_program", lambda _program: None)
    with pytest.raises(InvalidJumpError, match="instruction boundary"):
        VM(program).run()


def test_runtime_invalid_call_with_validation_disabled(monkeypatch):
    code = encode_instruction(OpCode.CALL, (9, 0)) + bytes([OpCode.HALT])
    program = Program(
        [],
        {
            "main": Function("main", 0, 0, code),
            "f": Function("f", 0, 0, bytes([OpCode.HALT])),
        },
    )
    monkeypatch.setattr("pvm.vm.validate_program", lambda _program: None)
    with pytest.raises(InvalidCallError, match="function index 9"):
        VM(program).run()


def test_runtime_call_arity_mismatch_with_validation_disabled(monkeypatch):
    code = encode_instruction(OpCode.CALL, (1, 2)) + bytes([OpCode.HALT])
    program = Program(
        [],
        {
            "main": Function("main", 0, 0, code),
            "f": Function("f", 1, 1, bytes([OpCode.HALT])),
        },
    )
    monkeypatch.setattr("pvm.vm.validate_program", lambda _program: None)
    with pytest.raises(InvalidCallError, match="expects 1 argument"):
        VM(program).run()


def test_runtime_ip_past_end_with_validation_disabled(monkeypatch):
    code = encode_instruction(OpCode.LOAD_CONST, (0,)) + encode_instruction(
        OpCode.JUMP, (0,)
    )
    program = Program([0], {"main": Function("main", 0, 0, code)})
    monkeypatch.setattr("pvm.vm.validate_program", lambda _program: None)
    vm = VM(program)

    def force_past_end(_target: int) -> None:
        vm.frame.ip = len(program.functions["main"].code)

    monkeypatch.setattr(vm, "_set_ip", force_past_end)
    with pytest.raises(VMError, match="ran past"):
        vm.run()


def test_vm_max_steps_zero_warns(capsys):
    from pvm.vm import VMConfig

    VM(
        assemble("func main 0 0\nHALT"),
        config=VMConfig(max_steps=0),
        output=lambda _: None,
    ).run()
    captured = capsys.readouterr()
    assert "warning:" in captured.err
    assert "max_steps is 0" in captured.err


def test_vm_frame_requires_active_frame():
    vm = VM(assemble("func main 0 0\nHALT"))
    vm.frames = []
    with pytest.raises(VMError, match="no active frame"):
        _ = vm.frame


def test_version_is_exported():
    import pvm

    assert pvm.__version__ == "1.0.4"
    assert "__version__" in pvm.__all__
