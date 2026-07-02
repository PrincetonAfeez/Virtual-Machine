"""Tests for the CLI."""

import pytest

from pvm.cli import main
from pvm.errors import StackUnderflowError


def test_cli_assemble_run_disasm_validate(tmp_path, capsys):
    source = tmp_path / "answer.asm"
    bytecode = tmp_path / "answer.bc"
    source.write_text(
        "func main 0 0\nLOAD_CONST 42\nPRINT\nHALT\n",
        encoding="utf-8",
    )

    assert main(["assemble", str(source), "-o", str(bytecode)]) == 0
    assert bytecode.exists()
    assert main(["run", str(bytecode)]) == 0
    assert main(["disasm", str(bytecode)]) == 0
    assert main(["validate", str(bytecode)]) == 0

    output = capsys.readouterr().out
    assert "Assembled" in output
    assert "42" in output
    assert "LOAD_CONST 42" in output
    assert "Valid PVM1 program" in output


def test_cli_expected_error_has_no_traceback(tmp_path, capsys):
    source = tmp_path / "bad.asm"
    source.write_text("func main 0 0\nPOP\nHALT\n", encoding="utf-8")
    assert main(["run", str(source)]) == 1
    captured = capsys.readouterr()
    assert "error: operand stack underflow" in captured.err
    assert "Traceback" not in captured.err


def test_cli_prints_booleans_in_lowercase(tmp_path, capsys):
    source = tmp_path / "bool.asm"
    source.write_text(
        "func main 0 0\n" "LOAD_CONST true\nPRINT\nLOAD_CONST false\nPRINT\nHALT\n",
        encoding="utf-8",
    )
    assert main(["run", str(source)]) == 0
    out = capsys.readouterr().out
    assert "true" in out
    assert "false" in out
    assert "True" not in out and "False" not in out


def test_cli_run_trace_writes_to_stderr(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text("func main 0 0\nLOAD_CONST 1\nPRINT\nHALT\n", encoding="utf-8")
    assert main(["run", str(source), "--trace"]) == 0
    captured = capsys.readouterr()
    assert "1" in captured.out
    assert "TRACE" in captured.err
    assert "TRACE" not in captured.out


def test_cli_profile_reports_statistics(tmp_path, capsys):
    source = tmp_path / "prog.asm"
    source.write_text(
        "func main 0 0\nLOAD_CONST 2\nLOAD_CONST 3\nADD\nPRINT\nHALT\n",
        encoding="utf-8",
    )
    assert main(["profile", str(source)]) == 0
    captured = capsys.readouterr()
    assert "5" in captured.out
    assert "instructions:" in captured.err
    assert "opcode counts:" in captured.err
    assert "max call depth: 1" in captured.err
    assert "instructions:" not in captured.out


def test_cli_profile_trace_writes_to_stderr(tmp_path, capsys):
    source = tmp_path / "prog.asm"
    source.write_text(
        "func main 0 0\nLOAD_CONST 1\nPRINT\nHALT\n",
        encoding="utf-8",
    )
    assert main(["profile", str(source), "--trace"]) == 0
    captured = capsys.readouterr()
    assert "1" in captured.out
    assert "TRACE" in captured.err
    assert "TRACE" not in captured.out


def test_cli_missing_file_is_clean(tmp_path, capsys):
    assert main(["run", str(tmp_path / "nope.bc")]) == 1
    captured = capsys.readouterr()
    assert "could not read" in captured.err
    assert "Traceback" not in captured.err


def test_cli_corrupt_bytecode_is_clean(tmp_path, capsys):
    bad = tmp_path / "bad.bc"
    bad.write_bytes(b"NOPErubbish")
    for command in ("run", "disasm", "validate"):
        assert main([command, str(bad)]) == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err


def test_cli_unwritable_output_is_clean(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text("func main 0 0\nLOAD_CONST 1\nHALT\n", encoding="utf-8")
    target = tmp_path / "missing_dir" / "out.bc"
    assert main(["assemble", str(source), "-o", str(target)]) == 1
    captured = capsys.readouterr()
    assert "could not write" in captured.err
    assert "Traceback" not in captured.err


def test_cli_entrypoint_flag(tmp_path, capsys):
    source = tmp_path / "boot.asm"
    source.write_text("func boot 0 0\nLOAD_CONST 11\nPRINT\nHALT\n", encoding="utf-8")
    assert main(["run", str(source), "--entrypoint", "boot"]) == 0
    assert "11" in capsys.readouterr().out


def test_cli_entrypoint_on_bytecode_warns(tmp_path, capsys):
    from pvm.assembler import assemble
    from pvm.bytecode import save_program

    source = tmp_path / "boot.asm"
    bytecode = tmp_path / "boot.bc"
    text = "func boot 0 0\nLOAD_CONST 3\nHALT\n"
    source.write_text(text, encoding="utf-8")
    save_program(assemble(text, entrypoint="boot"), str(bytecode))
    assert main(["run", str(bytecode), "--entrypoint", "main"]) == 0
    captured = capsys.readouterr()
    assert "warning:" in captured.err
    assert "--entrypoint" in captured.err


def test_cli_debug_flag_surfaces_traceback(tmp_path):
    source = tmp_path / "bad.asm"
    source.write_text("func main 0 0\nPOP\nHALT\n", encoding="utf-8")
    with pytest.raises(StackUnderflowError):
        main(["--debug", "run", str(source)])


def test_cli_disasm_and_validate_accept_entrypoint_for_asm(tmp_path, capsys):
    source = tmp_path / "boot.asm"
    source.write_text("func boot 0 0\nLOAD_CONST 9\nHALT\n", encoding="utf-8")
    assert main(["disasm", str(source), "--entrypoint", "boot"]) == 0
    disasm_out = capsys.readouterr().out
    assert "; entrypoint boot" in disasm_out
    assert main(["validate", str(source), "--entrypoint", "boot"]) == 0
    validate_out = capsys.readouterr().out
    assert "Valid PVM1 program" in validate_out


def test_cli_disasm_on_asm_source(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text("func main 0 0\nLOAD_CONST 1\nHALT\n", encoding="utf-8")
    assert main(["disasm", str(source)]) == 0
    assert "LOAD_CONST 1" in capsys.readouterr().out


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "1.0.5" in capsys.readouterr().out


def test_cli_help_epilog_mentions_entrypoint(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "entrypoint" in capsys.readouterr().out


def test_cli_module_main_entrypoint():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pvm.cli", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "1.0.5" in result.stdout


def test_configure_logging_formats_warnings(capsys):
    import logging

    from pvm.cli import configure_logging

    configure_logging()
    logging.getLogger("pvm.test").warning("diagnostic message")
    assert "warning: diagnostic message" in capsys.readouterr().err


def test_cli_execute_rejects_unknown_command():
    import argparse

    from pvm.cli import _execute

    with pytest.raises(AssertionError, match="unhandled command"):
        _execute(argparse.Namespace(command="nope"))
