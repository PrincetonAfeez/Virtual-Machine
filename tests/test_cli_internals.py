"""Tests for the CLI internals."""

import argparse
import sys

import pytest

from pvm.assembler import assemble
from pvm.bytecode import save_program
from pvm.cli import (
    _emit,
    _emit_profile,
    _emit_trace,
    _execute,
    _program_from_path,
    build_parser,
    main,
)


def test_build_parser_exposes_all_subcommands():
    parser = build_parser()
    commands = parser.parse_args(["assemble", "x.asm", "-o", "x.bc"])
    assert commands.command == "assemble"
    commands = parser.parse_args(["run", "x.bc"])
    assert commands.command == "run"
    commands = parser.parse_args(["disasm", "x.bc"])
    assert commands.command == "disasm"
    commands = parser.parse_args(["validate", "x.bc"])
    assert commands.command == "validate"
    commands = parser.parse_args(["profile", "x.bc"])
    assert commands.command == "profile"


def test_build_parser_entrypoint_on_supported_commands():
    parser = build_parser()
    for command in ("assemble", "run", "disasm", "validate", "profile"):
        argv = [command, "x.asm"]
        if command == "assemble":
            argv.extend(["-o", "x.bc"])
        args = parser.parse_args(argv + ["--entrypoint", "boot"])
        assert args.entrypoint == "boot"


def test_program_from_path_assembles_asm(tmp_path):
    source = tmp_path / "p.asm"
    source.write_text("func boot 0 0\nHALT\n", encoding="utf-8")
    program = _program_from_path(str(source), entrypoint="boot")
    assert program.entrypoint == "boot"


def test_program_from_path_loads_bytecode(tmp_path):
    source = tmp_path / "p.bc"
    save_program(assemble("func main 0 0\nHALT\n"), str(source))
    program = _program_from_path(str(source))
    assert program.entrypoint == "main"


def test_program_from_path_warns_on_bytecode_entrypoint(tmp_path, capsys):
    path = tmp_path / "p.bc"
    save_program(assemble("func boot 0 0\nHALT\n", entrypoint="boot"), str(path))
    _program_from_path(str(path), entrypoint="main")
    assert "warning:" in capsys.readouterr().err


def test_emit_helpers_write_expected_streams(capsys):
    _emit(True)
    _emit_trace("trace-line")
    _emit_profile("profile-line")
    captured = capsys.readouterr()
    assert captured.out.strip() == "true"
    assert "trace-line" in captured.err
    assert "profile-line" in captured.err


def test_execute_assemble_command(tmp_path, capsys):
    source = tmp_path / "p.asm"
    target = tmp_path / "p.bc"
    source.write_text("func main 0 0\nHALT\n", encoding="utf-8")
    code = _execute(
        argparse.Namespace(
            command="assemble",
            input=str(source),
            output=str(target),
            entrypoint=None,
        )
    )
    assert code == 0
    assert target.exists()
    assert "Assembled" in capsys.readouterr().out


def test_execute_validate_command(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text("func main 0 0\nHALT\n", encoding="utf-8")
    code = _execute(
        argparse.Namespace(
            command="validate",
            input=str(source),
            entrypoint=None,
        )
    )
    assert code == 0
    assert "Valid PVM1 program" in capsys.readouterr().out


def test_execute_disasm_command(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text("func main 0 0\nHALT\n", encoding="utf-8")
    code = _execute(
        argparse.Namespace(
            command="disasm",
            input=str(source),
            entrypoint=None,
        )
    )
    assert code == 0
    assert "func main" in capsys.readouterr().out


def test_execute_profile_command(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text(
        "func main 0 0\nLOAD_CONST 1\nPRINT\nHALT\n",
        encoding="utf-8",
    )
    code = _execute(
        argparse.Namespace(
            command="profile",
            input=str(source),
            entrypoint=None,
            trace=False,
        )
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "1" in captured.out
    assert "instructions:" in captured.err


def test_execute_run_command(tmp_path, capsys):
    source = tmp_path / "p.asm"
    source.write_text(
        "func main 0 0\nLOAD_CONST 2\nPRINT\nHALT\n",
        encoding="utf-8",
    )
    code = _execute(
        argparse.Namespace(
            command="run",
            input=str(source),
            entrypoint=None,
            trace=False,
        )
    )
    assert code == 0
    assert "2" in capsys.readouterr().out


def test_main_returns_one_on_assembler_error(tmp_path, capsys):
    source = tmp_path / "bad.asm"
    source.write_text("not assembly", encoding="utf-8")
    assert main(["run", str(source)]) == 1
    assert "error:" in capsys.readouterr().err


def test_main_default_argv_uses_sys_argv(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pvm", "--version"])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
