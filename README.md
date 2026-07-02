# PVM: a small stack-based virtual machine

**Author:** Princeton Afeez · **License:** [MIT](LICENSE) · **Context:** Python
systems-programming capstone

PVM is a stack-based virtual machine written in Python. It defines a compact
instruction set, a `PVM1` bytecode file, a two-pass assembler, a disassembler,
an iterative execution engine, defensive bytecode validation, VM-owned call
frames, and command-line tools. A local GitHub Actions workflow lives in
[`.github/workflows/ci.yml`](.github/workflows/ci.yml).

A stack machine keeps operands on a last-in, first-out stack. To calculate
`2 + 3`, PVM pushes both values and `ADD` pops them and pushes `5`. A
register-based machine would name registers containing those operands instead.

## Quick start

PVM requires Python 3.10 or newer. Runtime use has no third-party dependencies.

```console
python -m pip install -r requirements-dev.txt
pre-commit install
python -m pvm --version
python -m pvm assemble examples/factorial.asm -o factorial.bc
python -m pvm disasm factorial.bc
python -m pvm run factorial.bc
python -m pvm run examples/factorial.asm --trace
python -m pvm run program.asm --entrypoint boot
python -m pvm validate factorial.bc
python -m pvm profile factorial.bc
pytest
```

For runtime-only use (no dev tooling), `pip install -r requirements.txt` is
enough. The equivalent forms `pip install -e .` and `pip install -e ".[dev]"` also work.

The shorter `pvm ...` form is equivalent when Python's user scripts directory
is on `PATH`. `pvm --version` prints the release, and the global `--debug` flag
(e.g. `pvm --debug run program.bc`) is described under
[Errors and limits](#errors-and-limits).

The included programs print:

| Program | Result | Demonstrates |
|---|---:|---|
| `arithmetic.asm` | 14 | constants and arithmetic |
| `if_else.asm` | 100 | comparisons and conditional jumps |
| `loop.asm` | 15 | locals, labels, and loops |
| `factorial.asm` | 120 | recursive calls |
| `fibonacci.asm` | 55 | branching recursion |

Three deliberately broken programs exercise the failure paths: `bad_jump.asm`
is rejected by the assembler/validator because its jump target is not an
instruction boundary, while `bad_stack_underflow.asm` and `bad_div_zero.asm`
assemble cleanly and raise a `VMError` at run time.

## Project layout

```text
examples/              sample .asm programs (including deliberate failure demos)
src/pvm/               assembler, VM, bytecode format, CLI, and validation
tests/                 pytest suite (23 modules, 387 tests)
.github/workflows/     CI (ruff, ruff format, mypy, pytest, example smoke test)
.pre-commit-config.yaml local hooks mirroring CI
requirements.txt       editable install for runtime (no third-party deps)
requirements-dev.txt   editable install plus lint, type-check, and test tooling
pyproject.toml         package metadata and tool configuration
```

## Development

Install tooling and run the same checks as CI:

```console
python -m pip install -r requirements-dev.txt
pre-commit install          # optional: run hooks before each commit
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy
python -m pytest --cov=pvm --cov-report=term-missing --cov-fail-under=95
```

CI runs on Ubuntu with Python 3.10 through 3.14. Each matrix job lints, type-
checks, runs the full pytest suite (95% coverage gate), and smoke-tests
`examples/factorial.asm` through assemble → validate → run.

The test suite is organized by module: assembler, bytecode, CLI, disassembler,
errors, format, names, opcodes, program model, validate, VM handlers, and
example programs under `tests/test_*.py`.

## Demo

A full session, from source to recursive execution to a clean failure:

```console
$ pvm assemble examples/factorial.asm -o factorial.bc
Assembled 2 function(s) to factorial.bc

$ pvm disasm factorial.bc
func main 0 0
    LOAD_CONST 5  ; @0000
    CALL factorial 1  ; @0003
    PRINT  ; @0007
    HALT  ; @0008
...

$ pvm run factorial.bc
120

$ pvm validate factorial.bc
Valid PVM1 program: 2 function(s), 2 constant(s)

$ pvm run examples/bad_div_zero.asm
error: division by zero (function=main, ip=6, opcode=DIV)
$ echo $?
1
```

## Architecture

```text
assembly text ──> two-pass assembler ──> Program ──> PVM1 serializer
                                             │
                  disassembler <─────────────┤
                                             │ validated Program
                                             ▼
                                  fetch/decode/execute VM
                                  ├─ operand stacks
                                  ├─ local slots
                                  └─ VM call frames
```

The assembler never executes code. The VM never parses assembly. The
disassembler only renders validated bytecode. This separation lets the loader
treat every bytecode file as untrusted input.

## Assembly syntax

Functions begin with:

```text
func <name> <arity> <num_locals>
```

Labels end in `:` and are scoped to their function. Comments begin with `;`,
`#`, or `//`. `LOAD_CONST` accepts `true`/`false` or an integer written in
decimal, `0x` hex, `0o` octal, or `0b` binary (decimal integers must not carry
a leading zero); the assembler builds and deduplicates the constant pool. Local
slots are numeric.

```asm
func main 0 0
    LOAD_CONST 5
    CALL factorial 1
    PRINT
    HALT
```

The assembler's first pass records functions, byte offsets, and labels. Its
second pass creates the constant pool, resolves labels and function references,
and emits bytes. Disassembly renders synthetic `Lxxxx` labels and is
semantically equivalent to the original assembler output, but not text-identical
to hand-written source.

## Machine and call model

Each frame owns a function name, its own instruction pointer, an operand stack,
and local slots. `CALL` removes arguments from the caller stack and places them
in the callee's first local slots in push order—the first value pushed becomes
slot `0`, the next becomes slot `1`, and so on—then pushes a frame. Because the
caller's
instruction pointer lives in its own frame, `RETURN` simply discards the callee
frame and pushes its result onto the caller stack, resuming the caller where it
left off. The engine uses a Python `while` loop—not Python recursion—so
recursive guest programs are bounded by `max_call_depth`.

`RETURN` pops the result value and, when leaving `main`, sets `VM.run()`'s
return value. `HALT` stops without popping: if the operand stack is non-empty,
`VM.run()` returns the current top value; otherwise it returns `None`.

The VM uses table dispatch: each `OpCode` maps to a handler method. Other common
interpreter strategies are an `if/elif` chain, `match/case`, and, in lower-level
languages, threaded or computed-goto dispatch.

## Instruction reference

All binary operations pop `right` and then `left`.

| Instruction | Operands | Stack effect | Meaning |
|---|---|---|---|
| `LOAD_CONST` | literal | `[] -> [value]` | Push a pooled constant |
| `POP` | — | `[x] -> []` | Discard top |
| `DUP` | — | `[x] -> [x, x]` | Duplicate top |
| `SWAP` | — | `[a, b] -> [b, a]` | Swap top pair |
| `ADD SUB MUL DIV MOD` | — | `[int, int] -> [int]` | Integer arithmetic |
| `NEG` | — | `[int] -> [int]` | Negate |
| `EQ NE` | — | `[T, T] -> [bool]` | Equality of two ints or two bools |
| `LT LE GT GE` | — | `[int, int] -> [bool]` | Integer ordering |
| `AND OR` | — | `[bool, bool] -> [bool]` | Boolean logic |
| `NOT` | — | `[bool] -> [bool]` | Boolean negation |
| `LOAD_VAR` | slot | `[] -> [value]` | Read a local |
| `STORE_VAR` | slot | `[value] -> []` | Write a local |
| `JUMP` | label | unchanged | Unconditional jump |
| `JUMP_IF_FALSE` | label | `[bool] -> []` | Jump when false |
| `JUMP_IF_TRUE` | label | `[bool] -> []` | Jump when true |
| `CALL` | name, argc | `[args...] -> [result]` | Enter a function |
| `RETURN` | — | `[result] -> caller` | Leave a function |
| `PRINT` | — | `[value] -> []` | Print and remove top |
| `HALT` | — | unchanged | Stop the whole VM |

Arithmetic requires exact integers (booleans are not accepted as integers) and
uses Python's arbitrary-precision integers, so computed results are never
silently wrapped; only stored constants are range-checked to signed 64 bits.
`DIV` truncates toward zero, and `MOD` returns the matching remainder, so its
sign follows the dividend (`-8 MOD 3 == -2`). Logic requires exact booleans.
`EQ` and `NE` compare two values of the same type (two ints or two booleans),
while the ordering comparisons are integer-only. `PRINT` writes integers
directly and renders booleans with the lowercase `true`/`false` spelling used
by the assembly language.

## Bytecode format

Multi-byte integers use big-endian order. Instruction encoding is one opcode
byte followed by fixed-width operands:

- constant index and absolute jump target: 2 bytes
- local slot and argument count: 1 byte
- function table index: 2 bytes

The serialized file layout is:

```text
"PVM1" | version:u8 | entrypoint:text
constant_count:u16 | constants...
function_count:u16 | functions...

text     = byte_length:u16 | UTF-8 bytes
constant = type:u8 | bool:u8 OR signed_integer:i64
function = name:text | arity:u8 | locals:u8 | code_length:u32 | code
```

Because the count fields and table indexes are 16-bit, a program may hold at
most 65535 constants and 65535 functions. The format stores no debug metadata;
the disassembler reconstructs labels directly from each function's jump targets.

Validation rejects bad magic/version data, truncation, trailing data, unknown
opcodes, malformed operands, invalid constant/local/function indexes, jumps
that do not land on instruction boundaries, incorrect call arity, and function
or entrypoint names that are not ASCII identifiers matching
`[A-Za-z_][A-Za-z0-9_]*`. Stack sufficiency is not checked statically: programs
such as `ADD` on an empty stack assemble and validate, then fail at run time
with `StackUnderflowError` (see the `bad_stack_underflow.asm` example).

Disassembly emits a leading `; entrypoint <name>` comment so a disassembled
program can be reassembled with the same entry function. The CLI and library
also accept `--entrypoint` / `entrypoint=` on `assemble`, `run`, `profile`, `disasm`,
and `validate` to override the default `main` when the input is `.asm` source.
The `--entrypoint` flag applies only when assembling `.asm` source; bytecode
files carry their own entrypoint and the flag is ignored with a warning.

## Trace mode

`pvm run program.bc --trace` prints, for each step, the function that ran the
instruction, the pre-execution byte offset, the opcode, its encoded operands,
and—all describing that same frame—its post-execution operand stack, locals,
and call depth. Keeping every field tied to one frame makes calls and stack
effects easy to follow; a `CALL` or `RETURN` moves a value across frames, which
is visible by reading the adjacent lines. Trace lines are written to stderr, so
a program's own output on stdout stays clean and separately redirectable.
Library use: `VM(..., trace=True)` also defaults trace output to stderr unless
`trace_output=` is supplied.

## Profiling

`pvm profile program.bc` runs a program and reports execution statistics on
**stderr** (program output stays on stdout): the total instructions retired,
the deepest a single frame's operand stack grew, the deepest the call stack
grew, and a per-opcode execution count. It is a quick way to see the shape of
a run—for example, how much of `factorial` is `CALL`, `LE`, and `MUL`, or how
`max call depth` tracks recursion depth.

```console
$ pvm profile factorial.bc
120
instructions: 54
max stack depth: 3
max call depth: 6
opcode counts:
  LOAD_VAR      13
  LOAD_CONST    11
  CALL          5
  ...
```

The first line (`120`) is the program's own output on stdout; the statistics
lines are on stderr.

## Use as a library

Everything the CLI does is also available by importing `pvm`. The package
exports the assembler, VM, disassembler, bytecode (de)serializer, and the
`PVMError` hierarchy (see `pvm.__all__`).

```python
import pvm

program = pvm.assemble("""
func main 0 0
    LOAD_CONST 6
    CALL square 1
    PRINT
    HALT
func square 1 1
    LOAD_VAR 0
    LOAD_VAR 0
    MUL
    RETURN
""")

pvm.VM(
    program,
    output=lambda value: print(pvm.format_value(value)),
).run()                                   # prints 36

blob = pvm.serialize_program(program)      # PVM1 bytes
restored = pvm.deserialize_program(blob)   # validated on load
print(pvm.disassemble(restored))

try:
    pvm.assemble("func main 0 0\n    LOAD_CONST 1")   # no terminator
except pvm.PVMError as exc:
    print("rejected:", exc)
```

`VM(program, output=...)` accepts a callback to capture printed values instead
of writing to stdout. Use `pvm.format_value` for the same lowercase boolean
spelling the CLI uses. `VM(program, config=pvm.VMConfig(...))` overrides the
stack, call-depth, and step limits.

When building a `Program` manually, keep `functions` dict insertion order
aligned with `CALL` operand indexes (index `0` is the first function in the
dict). The loader and serializer preserve file order; only hand-built programs
need care.

## Errors and limits

Expected failures use the `PVMError` hierarchy and the CLI reports them without
a traceback, as `error: <message>` on stderr with exit status 1. The global
`--debug` flag (placed before the subcommand, e.g. `pvm --debug run prog.bc`)
re-raises the underlying exception with its full traceback for development.
VM errors include function, instruction pointer, and opcode context. Three
configurable limits stop runaway programs: a per-frame operand-stack bound
(`max_stack_depth`, so peak operand memory is at most
`max_call_depth × max_stack_depth`), a call-depth bound that catches infinite
recursion before Python's own, and a total instruction-step bound
(`max_steps`, set to `0` to disable) that catches infinite loops which grow
neither the stack nor the call depth. Setting `max_steps` to `0` emits a
warning and allows infinite loops to run until externally interrupted.

## Known limitations and roadmap

Core values are integers and booleans. There are no objects, closures, garbage
collection, modules, threads, or source-language compiler. Disassembly round-
trips assembler-produced programs exactly. Hand-built bytecode that lists unused
constants in the pool is not reproduced verbatim, because the disassembler emits
only constants referenced by `LOAD_CONST`. Natural follow-on work includes a
SHA-256 bytecode digest, control-flow graphs and unreachable-code reporting,
an interactive debugger, and—only after those—a small Django/HTMX visual stepper.
