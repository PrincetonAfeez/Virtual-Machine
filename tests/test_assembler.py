"""Tests for the assembler."""

import pytest

from pvm.assembler import assemble, assemble_file
from pvm.disassembler import disassemble
from pvm.errors import AssemblerError
from pvm.opcodes import OpCode, iter_instructions


def test_labels_resolve_to_absolute_instruction_offsets():
    program = assemble(
        """
        func main 0 0
        start:
            LOAD_CONST true
            JUMP_IF_TRUE start
            HALT
        """
    )
    instructions = iter_instructions(program.functions["main"].code)
    assert instructions[1][1] is OpCode.JUMP_IF_TRUE
    assert instructions[1][2] == (0,)
    assert program.constants == [True]


def test_constant_deduplication_preserves_bool_and_int_types():
    program = assemble(
        """
        func main 0 0
            LOAD_CONST 1
            LOAD_CONST true
            LOAD_CONST 1
            HALT
        """
    )
    assert program.constants == [1, True]
    assert [type(value) for value in program.constants] == [int, bool]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("func main 0 0\nNOPE", "unknown mnemonic"),
        ("func main 0 0\nADD 1", "expects 0 operand"),
        ("func main 0 0\nJUMP missing\nHALT", "undefined label"),
        ("func main 0 0\nCALL missing 0\nHALT", "undefined function"),
        ("func main 0 0\nLOAD_VAR 0\nHALT", "local slot 0"),
        ("func main 0 0\nx:\nx:\nHALT", "duplicate label"),
        ("func main 0 0\nHALT\nfunc main 0 0\nHALT", "duplicate function"),
    ],
)
def test_helpful_assembly_errors(source, message):
    with pytest.raises(AssemblerError, match=message):
        assemble(source)


def test_crlf_source_assembles():
    program = assemble("func main 0 0\r\n    LOAD_CONST 7\r\n    HALT\r\n")
    assert program.constants == [7]


def test_comment_only_source_is_rejected_cleanly():
    with pytest.raises(AssemblerError, match="no functions"):
        assemble("; just a comment\n\n   \n")


def test_missing_terminator_is_rejected_with_line():
    with pytest.raises(AssemblerError, match="must end with") as excinfo:
        assemble("func main 0 0\n    LOAD_CONST 1\n")
    assert excinfo.value.line is not None


def test_call_with_wrong_arity_is_rejected():
    with pytest.raises(AssemblerError, match="expects 1 argument"):
        assemble(
            "func main 0 0\n"
            "    LOAD_CONST 1\n"
            "    CALL f 2\n"
            "    HALT\n"
            "func f 1 1\n"
            "    LOAD_VAR 0\n"
            "    RETURN\n"
        )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("func 1bad 0 0\nHALT", "invalid function name"),
        ("func main 300 300\nHALT", "between 0 and 255"),
        ("func main 2 1\nLOAD_VAR 0\nRETURN", "local count cannot be smaller"),
        ("LOAD_CONST 1\nHALT", "outside a function"),
        ("func main 0 0\nLOAD_CONST abc\nHALT", "invalid constant"),
        ("func main 0 0\n1bad:\nHALT", "invalid label"),
        ("func main 0\nHALT", "must be: func"),
        ("func main 0 0\nfunc other 0 0\nHALT", "contains no instructions"),
        ("func main 0 0\nJUMP -1\nHALT", "cannot be negative"),
        ("func foo 0 0\nHALT", "entrypoint 'main'"),
    ],
)
def test_more_assembly_errors(source, message):
    with pytest.raises(AssemblerError, match=message):
        assemble(source)


def test_missing_main_reports_line_number():
    with pytest.raises(AssemblerError, match="entrypoint 'main'") as excinfo:
        assemble("func foo 0 0\nHALT")
    assert excinfo.value.line == 1


def test_oversized_constant_reports_line_number():
    with pytest.raises(AssemblerError, match="64-bit") as excinfo:
        assemble("func main 0 0\nLOAD_CONST 9223372036854775808\nHALT")
    assert excinfo.value.line == 2


@pytest.mark.parametrize("token", ["012", "007", "00"])
def test_leading_zero_constant_is_rejected(token):
    with pytest.raises(AssemblerError, match="invalid constant"):
        assemble(f"func main 0 0\nLOAD_CONST {token}\nHALT")


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("0x10", 16),
        ("0o10", 8),
        ("0b1010", 10),
        ("-0x2", -2),
    ],
)
def test_prefixed_numeric_constants_are_accepted(token, expected):
    program = assemble(f"func main 0 0\nLOAD_CONST {token}\nHALT")
    assert program.constants == [expected]


def test_hash_and_slash_entrypoint_directives(tmp_path):
    program = assemble("# entrypoint boot\nfunc boot 0 0\nHALT\n")
    assert program.entrypoint == "boot"
    program = assemble("// entrypoint boot\nfunc boot 0 0\nHALT\n")
    assert program.entrypoint == "boot"


def test_assemble_file_tolerates_utf8_bom(tmp_path):
    path = tmp_path / "bom.asm"
    path.write_bytes("\ufefffunc main 0 0\nHALT\n".encode())
    program = assemble_file(str(path))
    assert program.entrypoint == "main"


def test_assemble_file_rejects_invalid_utf8(tmp_path):
    path = tmp_path / "bad.asm"
    path.write_bytes(b"func main 0 0\nLOAD_CONST \xff\nHALT\n")
    with pytest.raises(AssemblerError, match="invalid UTF-8"):
        assemble_file(str(path))


def test_too_many_functions_reports_line_number():
    source = "\n".join(f"func f{i} 0 0\n    HALT" for i in range(65536))
    with pytest.raises(AssemblerError, match="65535 functions") as excinfo:
        assemble(source)
    assert excinfo.value.line is not None


def test_numeric_jump_to_non_boundary_is_rejected():
    with pytest.raises(AssemblerError, match="instruction boundary"):
        assemble("func main 0 0\nJUMP 1\nHALT")


def test_entrypoint_directive_is_honored():
    program = assemble(
        "; entrypoint boot\n" "func boot 0 0\n" "    LOAD_CONST 7\n" "    HALT\n"
    )
    assert program.entrypoint == "boot"


def test_custom_entrypoint_parameter_overrides_directive():
    program = assemble(
        "; entrypoint boot\n"
        "func boot 0 0\n"
        "    HALT\n"
        "func main 0 0\n"
        "    HALT\n",
        entrypoint="main",
    )
    assert program.entrypoint == "main"


def test_custom_entrypoint_round_trips_through_disassembler():
    program = assemble(
        "func boot 0 0\nLOAD_CONST 9\nHALT",
        entrypoint="boot",
    )
    text = disassemble(program)
    assert text.startswith("; entrypoint boot\n")
    assert assemble(text) == program


def test_invalid_entrypoint_directive_is_rejected():
    with pytest.raises(
        AssemblerError, match="invalid entrypoint name '9bad'"
    ) as excinfo:
        assemble("; entrypoint 9bad\nfunc main 0 0\nHALT")
    assert excinfo.value.line == 1


def test_bare_entrypoint_directive_is_rejected():
    with pytest.raises(AssemblerError, match="requires a function name") as excinfo:
        assemble("; entrypoint\nfunc main 0 0\nHALT")
    assert excinfo.value.line == 1


def test_missing_entrypoint_uses_directive_line():
    with pytest.raises(AssemblerError, match="does not exist") as excinfo:
        assemble("; entrypoint missing\nfunc main 0 0\nHALT")
    assert excinfo.value.line == 1


def test_conflicting_entrypoint_directives_are_rejected():
    source = (
        "; entrypoint boot\n"
        "; entrypoint main\n"
        "func boot 0 0\nHALT\n"
        "func main 0 0\nHALT"
    )
    with pytest.raises(AssemblerError, match="conflicting entrypoint") as excinfo:
        assemble(source)
    assert excinfo.value.line == 2


def test_post_function_entrypoint_directive_is_rejected():
    with pytest.raises(AssemblerError, match="before the first function") as excinfo:
        assemble("func main 0 0\n; entrypoint boot\nHALT")
    assert excinfo.value.line == 2


def test_invalid_entrypoint_parameter_is_rejected():
    with pytest.raises(
        AssemblerError, match="invalid entrypoint name '9bad'"
    ) as excinfo:
        assemble("func main 0 0\nHALT", entrypoint="9bad")
    assert excinfo.value.line == 1


def test_invalid_entrypoint_parameter_name_is_rejected():
    with pytest.raises(
        AssemblerError, match="invalid entrypoint name 'bad-name'"
    ) as excinfo:
        assemble("func main 0 0\nHALT", entrypoint="bad-name")
    assert excinfo.value.line == 1


def test_entrypoint_arity_error_reports_line():
    with pytest.raises(AssemblerError, match="must have arity 0") as excinfo:
        assemble("func main 1 1\nLOAD_VAR 0\nRETURN")
    assert excinfo.value.line == 1


def test_duplicate_identical_entrypoint_directive_is_rejected():
    with pytest.raises(AssemblerError, match="duplicate entrypoint directive"):
        assemble("; entrypoint main\n; entrypoint main\nfunc main 0 0\nHALT")


def test_negative_local_slot_reports_non_negative_error():
    with pytest.raises(AssemblerError, match="must be non-negative"):
        assemble("func main 0 1\nLOAD_VAR -1\nHALT")


def test_negative_call_argument_count_reports_non_negative_error():
    with pytest.raises(AssemblerError, match="must be non-negative"):
        assemble("func main 0 0\nCALL f -1\nHALT\nfunc f 0 0\nHALT")


def test_assembler_surfaces_final_validation_errors_with_line(monkeypatch):
    from pvm.errors import BytecodeValidationError

    def boom(_program):
        raise BytecodeValidationError("synthetic validation failure")

    monkeypatch.setattr("pvm.assembler.validate_program", boom)
    with pytest.raises(AssemblerError, match="synthetic validation") as excinfo:
        assemble("func main 0 0\nHALT")
    assert excinfo.value.line == 1


def test_disassemble_omits_unreferenced_constants():
    from pvm.program import Function, Program

    code = bytes([OpCode.LOAD_CONST, 0, 0, OpCode.HALT])
    program = Program([1, 999], {"main": Function("main", 0, 0, code)})
    text = disassemble(program)
    assert "LOAD_CONST 1" in text
    assert "999" not in text
    assert assemble(text).constants == [1]


def test_too_many_functions_rejected():
    source = "\n".join(f"func f{i} 0 0\n    HALT" for i in range(65536))
    with pytest.raises(AssemblerError, match="65535 functions"):
        assemble(source)


def test_constant_table_full():
    loads = "\n".join(f"    LOAD_CONST {index}" for index in range(65536))
    source = f"func main 0 0\n{loads}\n    HALT"
    with pytest.raises(AssemblerError, match="constant table is full") as excinfo:
        assemble(source)
    assert excinfo.value.line is not None


def test_assembler_surfaces_encode_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError("operand does not fit")

    monkeypatch.setattr("pvm.assembler.encode_instruction", boom)
    with pytest.raises(AssemblerError, match="does not fit") as excinfo:
        assemble("func main 0 0\nHALT")
    assert excinfo.value.line == 2


def test_assemble_file_missing_path_is_clean():
    with pytest.raises(AssemblerError, match="could not read"):
        assemble_file("definitely_does_not_exist.asm")


def test_inline_label_on_same_line_as_instruction():
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST true\n"
        "loop: JUMP_IF_FALSE loop\n"
        "    HALT\n"
    )
    instructions = iter_instructions(program.functions["main"].code)
    # The label and the instruction it precedes share the same offset.
    assert instructions[1][1] is OpCode.JUMP_IF_FALSE


def test_disassemble_renders_labels_booleans_and_multiple_functions():
    program = assemble(
        "func main 0 0\n"
        "    LOAD_CONST true\n"
        "    JUMP_IF_FALSE done\n"
        "    LOAD_CONST 1\n"
        "    PRINT\n"
        "done:\n"
        "    HALT\n"
        "func f 0 0\n"
        "    LOAD_CONST false\n"
        "    POP\n"
        "    HALT\n"
    )
    text = disassemble(program)
    assert text.startswith("; entrypoint main\n")
    assert "LOAD_CONST true" in text
    assert "LOAD_CONST false" in text
    assert "func f 0 0" in text
    assert "JUMP_IF_FALSE L" in text
    assert assemble(text) == program


def test_assemble_disassemble_assemble_is_stable():
    source = """
    func main 0 0
        LOAD_CONST 5
        CALL double 1
        PRINT
        HALT
    func double 1 1
        LOAD_VAR 0
        LOAD_CONST 2
        MUL
        RETURN
    """
    original = assemble(source)
    rebuilt = assemble(disassemble(original))
    assert rebuilt == original
