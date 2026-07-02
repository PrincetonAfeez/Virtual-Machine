"""Command-line interface for PVM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .assembler import assemble_file
from .bytecode import load_program, save_program
from .disassembler import disassemble
from .errors import PVMError
from .format import format_value
from .program import Program
from .validate import validate_program
from .vm import VM


def _program_from_path(path: str, *, entrypoint: str | None = None) -> Program:
    path_obj = Path(path)
    if path_obj.suffix.lower() == ".asm":
        return assemble_file(path, entrypoint=entrypoint)
    if entrypoint is not None:
        print(
            "warning: --entrypoint applies only when assembling .asm source; "
            "using the entrypoint stored in the bytecode file",
            file=sys.stderr,
        )
    return load_program(path)


def _emit(value: object) -> None:
    print(format_value(value))


def _emit_trace(line: object) -> None:
    # Trace telemetry goes to stderr so program output on stdout stays clean.
    print(line, file=sys.stderr)


def _emit_profile(line: object) -> None:
    # Profile statistics go to stderr so stdout can capture program output only.
    print(line, file=sys.stderr)


def _add_entrypoint_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--entrypoint",
        default=None,
        help="entry function when input is .asm (default: main or ; entrypoint)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pvm",
        description="Assemble and run PVM stack-machine programs",
        epilog=(
            "The --entrypoint flag applies when assembling .asm source. "
            "Bytecode files carry their own entrypoint."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--debug", action="store_true", help="show internal tracebacks")
    parser.add_argument("--version", action="version", version=f"pvm {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    assemble_parser = subparsers.add_parser(
        "assemble", help="assemble source into a PVM1 bytecode file"
    )
    assemble_parser.add_argument("input")
    assemble_parser.add_argument("-o", "--output", required=True)
    _add_entrypoint_option(assemble_parser)

    run_parser = subparsers.add_parser("run", help="run .asm or .bc input")
    run_parser.add_argument("input")
    run_parser.add_argument(
        "--trace", action="store_true", help="trace every executed instruction"
    )
    _add_entrypoint_option(run_parser)

    disasm_parser = subparsers.add_parser(
        "disasm", help="disassemble .asm or .bc input"
    )
    disasm_parser.add_argument("input")
    _add_entrypoint_option(disasm_parser)

    validate_parser = subparsers.add_parser(
        "validate", help="validate .asm or .bc input"
    )
    validate_parser.add_argument("input")
    _add_entrypoint_option(validate_parser)

    profile_parser = subparsers.add_parser(
        "profile", help="run a program and report execution statistics"
    )
    profile_parser.add_argument("input")
    profile_parser.add_argument(
        "--trace", action="store_true", help="trace every executed instruction"
    )
    _add_entrypoint_option(profile_parser)
    return parser


def _execute(args: argparse.Namespace) -> int:
    entrypoint = getattr(args, "entrypoint", None)
    if args.command == "assemble":
        program = assemble_file(args.input, entrypoint=entrypoint)
        save_program(program, args.output)
        print(f"Assembled {len(program.functions)} function(s) to {args.output}")
        return 0
    if args.command == "run":
        program = _program_from_path(args.input, entrypoint=entrypoint)
        VM(
            program,
            output=_emit,
            trace=args.trace,
            trace_output=_emit_trace,
        ).run()
        return 0
    if args.command == "disasm":
        sys.stdout.write(
            disassemble(_program_from_path(args.input, entrypoint=entrypoint))
        )
        return 0
    if args.command == "validate":
        program = _program_from_path(args.input, entrypoint=entrypoint)
        validate_program(program)
        print(
            f"Valid PVM1 program: {len(program.functions)} function(s), "
            f"{len(program.constants)} constant(s)"
        )
        return 0
    if args.command == "profile":
        program = _program_from_path(args.input, entrypoint=entrypoint)
        vm = VM(
            program,
            output=_emit,
            trace=args.trace,
            trace_output=_emit_trace,
        )
        vm.run()
        _emit_profile(f"instructions: {vm.instruction_count}")
        _emit_profile(f"max stack depth: {vm.max_stack_seen}")
        _emit_profile(f"max call depth: {vm.max_call_depth_seen}")
        _emit_profile("opcode counts:")
        for opcode, count in sorted(
            vm.opcode_counts.items(), key=lambda item: (-item[1], item[0].name)
        ):
            _emit_profile(f"  {opcode.name:<14}{count}")
        return 0
    raise AssertionError(f"unhandled command {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _execute(args)
    except PVMError as exc:
        if args.debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
