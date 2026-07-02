"""Tests for the public API."""

import importlib
import subprocess
import sys

import pytest

import pvm


def test_public_exports_match_all():
    expected = {
        "AssemblerError",
        "BytecodeValidationError",
        "CallDepthError",
        "DivisionByZeroError",
        "Function",
        "InvalidCallError",
        "InvalidJumpError",
        "PVMError",
        "Program",
        "StackOverflowError",
        "StackUnderflowError",
        "StepLimitError",
        "TypeMismatchError",
        "UninitializedLocalError",
        "VM",
        "VMConfig",
        "VMError",
        "assemble",
        "assemble_file",
        "deserialize_program",
        "disassemble",
        "format_value",
        "load_program",
        "save_program",
        "serialize_program",
        "validate_program",
        "__version__",
    }
    assert set(pvm.__all__) == expected
    for name in pvm.__all__:
        assert hasattr(pvm, name)


def test_version_is_exported():
    assert pvm.__version__ == "1.0.5"


def test_main_module_invokes_cli(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "argv", ["pvm"])
    with pytest.raises(SystemExit) as excinfo:
        from pvm.cli import main

        main()
    assert excinfo.value.code == 2


def test_package_main_entrypoint():
    result = subprocess.run(
        [sys.executable, "-m", "pvm", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "1.0.5" in result.stdout


def test_reload_preserves_version():
    reloaded = importlib.reload(importlib.import_module("pvm"))
    assert reloaded.__version__ == "1.0.5"
