# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.5] - 2026-06-19

### Changed
- `Development Status` classifier set to Beta (portfolio/academic maturity, not
  production-service claims).
- VM and CLI diagnostics use `logging` instead of direct `print`; the CLI
  configures a stderr warning handler so users still see messages.
- Added ADR 0001 documenting assembler/validator/disassembler/VM separation.
- Added `requirements-lock.txt` for reproducible development installs.
- README documents exit codes and the lockfile.

## [1.0.4] - 2026-06-19

### Fixed
- Decimal `LOAD_CONST` literals with a leading zero are rejected explicitly on
  all supported Python versions (not only where `int(..., 0)` happens to fail).
- Invalid UTF-8 in `.asm` files surfaces as `AssemblerError` through the CLI.
- Runtime invalid-jump errors use the same "instruction boundary" wording as
  the assembler and validator.

### Changed
- `--entrypoint` is available on `disasm` and `validate` for `.asm` inputs.
- Function-table overflow errors include a source line number.
- Test suite expanded to 387 tests across 23 modules with 100% line coverage
  of `src/pvm` (95% gate in CI and pre-commit).
- Added `requirements.txt` and `requirements-dev.txt`; CI installs from the
  latter and smoke-tests `examples/factorial.asm`.
- README documents development setup, test layout, and CI steps; `pyproject.toml`
  adds classifiers, keywords, and coverage report settings.

## [1.0.3] - 2026-06-19

### Fixed
- Negative local slots and `CALL` argument counts report a clear
  non-negative error instead of a generic out-of-range/arity message.
- Duplicate identical `; entrypoint` directives are rejected.

### Changed
- Removed GitHub-specific badge and URLs; metadata points to local docs.
- README portfolio header, project layout, and `--entrypoint` quick-start
  example.
- `--entrypoint` is offered on `assemble`, `run`, `profile`, `disasm`, and
  `validate` for `.asm` source; global CLI help documents bytecode behavior.
- `VM.run()` warns when `max_steps` is `0`.
- CI adds Python 3.14, `ruff format --check`, and a pre-commit config.

## [1.0.2] - 2026-06-19

### Fixed
- Bare `; entrypoint` comments without a name are rejected instead of silently
  defaulting to `main`.
- Missing-entrypoint errors cite the directive line, not the first `func` line.
- API `entrypoint=` parameter errors include line `1`; final assembler
  validation errors include the first function line.
- Restored `.gitignore` entry for `revised_virtual_machine_scope.txt`.
- `format_value` accepts only `int` and `bool`.

### Changed
- `profile` supports `--trace`; README notes disassembly label normalization
  and manual `Program` dict ordering.
- Published `[project.urls]` and CHANGELOG release links as local file anchors.

## [1.0.1] - 2026-06-19

### Fixed
- Entrypoint directives: reject invalid, duplicate/conflicting, and post-function
  forms with line numbers; validate identifier before existence checks.
- Entrypoint arity errors now report the function's source line during assembly.
- CLI warns when `--entrypoint` is passed with a `.bc` file (flag is assembly-only).
- Library `VM(trace=True)` defaults trace output to stderr.
- Disassembler uses shared `format_value`; docstring notes unused constants are
  omitted.
- README library example, trace notes, and known limitations aligned with
  current behavior.

### Changed
- Export `__version__` from `pvm.__all__`.
- Add `[project.urls]` metadata in `pyproject.toml`.

## [1.0.0] - 2026-06-19

Initial release.

### Added
- Stack-based virtual machine with an iterative fetch-decode-execute loop and
  table dispatch; guest recursion runs on VM-owned call frames, not Python
  recursion.
- Custom instruction set covering constants/stack, arithmetic, comparison and
  logic, locals, control flow, function calls, and I/O.
- Two-pass assembler with labels, function declarations, and line-numbered
  error messages.
- Disassembler that renders validated bytecode back to readable assembly and
  round-trips assembler-produced programs.
- `PVM1` binary bytecode format with `serialize`/`deserialize` and file load/save.
- Defensive validation that treats bytecode as untrusted input and rejects
  malformed programs with a clean `BytecodeValidationError`.
- Configurable runtime limits: `max_stack_depth`, `max_call_depth`, and
  `max_steps` (stops infinite loops).
- `pvm` command-line interface: `assemble`, `run`, `disasm`, `validate`, and
  `profile`, plus the `--trace`, `--debug`, `--version`, and `--entrypoint`
  flags.
- Public Python API exported from the `pvm` package (`assemble`, `VM`,
  `disassemble`, `format_value`, `serialize_program`/`deserialize_program`,
  the error hierarchy, and more).
- Example programs, a pytest suite, GitHub Actions CI (ruff, `mypy --strict`,
  pytest with a coverage gate), an MIT license, and a `py.typed` marker.

### Fixed
- Added the missing `py.typed` PEP 561 marker.
- Assembler errors for missing entrypoints and out-of-range integer constants
  now include source line numbers.
- Disassembly emits `; entrypoint <name>` so non-`main` programs round-trip.
- Profile statistics are written to stderr so stdout captures program output
  only.
- Bytecode validation rejects non-ASCII function and entrypoint names.

[1.0.5]: #105---2026-06-19
[1.0.4]: #104---2026-06-19
[1.0.3]: #103---2026-06-19
[1.0.2]: #102---2026-06-19
[1.0.1]: #101---2026-06-19
[1.0.0]: #100---2026-06-19
