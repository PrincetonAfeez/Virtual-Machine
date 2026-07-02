# Architecture Decision Record
## App — Virtual Machine
**Bytecode Runtime Systems Group | Document 1 of 5**
**Status: Accepted**

---

## Context

The Bytecode Runtime Systems group requires a portfolio-ready virtual machine that demonstrates interpreter architecture without hiding behind Python's own bytecode machinery. The project must define an instruction set, assembly syntax, bytecode format, validation boundary, execution engine, call frames, disassembly, profiling, trace output, command-line tooling, and a library API.

The project is **PVM**, a small stack-based virtual machine written in Python. It defines a compact instruction set, a `PVM1` bytecode file format, a two-pass assembler, a disassembler, an iterative fetch/decode/execute VM, defensive validation, VM-owned call frames, and CLI commands for assemble, run, disassemble, validate, and profile.

The selected architecture separates the system into stages:

```text
assembly text -> two-pass assembler -> Program -> PVM1 serializer
                                                -> validator
                                                -> iterative VM
                                                -> disassembler
```

The assembler never executes code. The VM never parses assembly. The bytecode loader treats every file as untrusted input and validates before execution.

---

## Decisions

### Decision 1 — Build a stack-based VM

**Chosen:** Use an operand stack model.

**Rejected:** Register-based VM.

**Reason:** A stack machine keeps the instruction format compact and makes the execution model easy to inspect. Arithmetic instructions pop operands and push results without naming registers.

### Decision 2 — Use a compact custom ISA

**Chosen:** Define a small opcode set covering constants, stack manipulation, arithmetic, comparison, boolean logic, locals, jumps, calls, return, print, and halt.

**Rejected:** Emulating Python bytecode or JVM bytecode.

**Reason:** A custom ISA is easier to audit, validate, document, test, and explain. It keeps the capstone focused on interpreter fundamentals instead of compatibility.

### Decision 3 — Use fixed-width bytecode operands

**Chosen:** Encode instruction operands with fixed byte widths: constant indexes and jump targets are 2 bytes, local slots and argument counts are 1 byte, and function indexes are 2 bytes.

**Rejected:** Variable-length integer encodings.

**Reason:** Fixed widths make instruction decoding deterministic and simple. The bytecode format is small but easy to validate.

### Decision 4 — Use big-endian byte order

**Chosen:** Encode multibyte numeric fields in big-endian order.

**Rejected:** Host-native byte order.

**Reason:** Bytecode should be platform-independent. Big-endian network-style ordering is conventional and predictable.

### Decision 5 — Store programs in an explicit `Program` model

**Chosen:** Use `Program`, `Function`, and a constant pool.

**Rejected:** Passing raw bytes directly into the VM.

**Reason:** The in-memory program model is easier to validate, inspect, disassemble, serialize, and execute.

### Decision 6 — Use a `PVM1` bytecode container

**Chosen:** Serialize programs with magic bytes, version, entrypoint, constant table, and function table.

**Rejected:** Storing only raw instruction bytes.

**Reason:** A bytecode file needs enough metadata to reconstruct a complete executable program.

### Decision 7 — Treat bytecode as untrusted input

**Chosen:** Validate bytecode after load and again before VM execution.

**Rejected:** Trusting assembler-produced or loader-produced programs.

**Reason:** A loader or caller can produce invalid in-memory structures. The VM boundary should be defensive even when earlier stages already validated.

### Decision 8 — Keep stack sufficiency as a runtime check

**Chosen:** Validator checks structural validity, indexes, arity, instruction boundaries, entrypoint, and control-flow termination, but stack underflow/type mismatch can fail at runtime.

**Rejected:** Full static stack analysis.

**Reason:** Full stack analysis across branches and calls would significantly expand scope. Runtime checks still produce precise VM errors with function/IP/opcode context.

### Decision 9 — Make the assembler two-pass

**Chosen:** First pass records functions, labels, instruction offsets, and code sizes. Second pass resolves constants, labels, function references, and emits bytes.

**Rejected:** One-pass assembler with scattered backpatching.

**Reason:** Two passes make label/function resolution clearer and give better line-numbered errors.

### Decision 10 — Deduplicate constants by exact type and value

**Chosen:** Constant pool deduplication uses `(type, value)` so `true` and `1` remain distinct.

**Rejected:** Deduplicating only by equality.

**Reason:** In Python, `True == 1`; the VM's type system must not collapse booleans and integers.

### Decision 11 — Limit stored constants to signed 64-bit integers

**Chosen:** Assembly integer literals stored in bytecode must fit in signed 64-bit range.

**Rejected:** Arbitrary-precision constant serialization.

**Reason:** The bytecode format uses fixed-width `i64` constant storage. Runtime arithmetic may produce arbitrary-precision Python integers, but serialized constants stay bounded.

### Decision 12 — Use VM-owned call frames

**Chosen:** Each frame owns function name, instruction pointer, local slots, and operand stack.

**Rejected:** Using Python recursion as the guest call stack.

**Reason:** Guest recursion must be controlled by VM limits. VM-owned frames make call depth, locals, return behavior, and tracing explicit.

### Decision 13 — Execute iteratively

**Chosen:** Use a Python `while` loop with fetch/decode/dispatch.

**Rejected:** Recursive evaluation.

**Reason:** Iterative execution prevents guest recursion from consuming Python stack frames and allows explicit `max_call_depth` and `max_steps` limits.

### Decision 14 — Use table dispatch

**Chosen:** Map every `OpCode` to a handler method.

**Rejected:** Long `if/elif` chain.

**Reason:** Table dispatch keeps the execution loop short and makes opcode coverage visible.

### Decision 15 — Use strict runtime types

**Chosen:** Exact integers are required for arithmetic/order operations, exact booleans for boolean operations, and equality compares values of the same type only.

**Rejected:** Letting Python's bool/int relationship blur VM types.

**Reason:** The VM's language has two value types. Python's `bool` is a subclass of `int`, but the VM should keep them separate.

### Decision 16 — Support trace and profile as first-class tools

**Chosen:** Trace prints each executed instruction with function, IP, opcode, operands, stack, locals, and call depth. Profile reports instruction count, max stack depth, max call depth, and opcode counts.

**Rejected:** Only running programs.

**Reason:** An educational VM should make execution visible. Trace/profile also help reviewers confirm the interpreter's behavior.

---

## Consequences

**Positive:**
- The VM has a clear, auditable ISA.
- Assembly, bytecode, validation, disassembly, and execution are separated.
- Bytecode files are portable and versioned.
- Untrusted bytecode is validated defensively.
- Runtime errors include machine context.
- Recursive guest programs are bounded by VM limits.
- Trace/profile modes make execution observable.
- CLI and library APIs expose the same core capabilities.

**Negative / Trade-offs:**
- The VM is intentionally small.
- No objects, closures, strings, arrays, heap, garbage collection, modules, threads, or high-level compiler.
- Static validation does not prove stack safety.
- Bytecode format stores no debug metadata.
- Disassembly of hand-built bytecode with unused constants is semantically equivalent but not byte-for-byte source-preserving.
- Function table insertion order matters when constructing `Program` manually.

---

## Alternatives Not Explored

- Register VM.
- SSA or IR runtime.
- JIT compilation.
- Python bytecode compatibility.
- WASM compatibility.
- Garbage-collected heap.
- Module loader.
- Object system.
- Debugger UI.
- Django/HTMX visual stepper.
- Control-flow graph analysis.
- Static stack-depth verifier.
- SHA-256 bytecode digest.

---

*Constitution reference: Article 1 (Python fundamentals and architectural thinking), Article 3.3 (scope discipline), Article 4 (quality proportional to scope), Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity).*

---


# Technical Design Document
## App — Virtual Machine
**Bytecode Runtime Systems Group | Document 2 of 5**

---

## Overview

PVM is a small stack-based virtual machine with a custom assembly language, `PVM1` bytecode format, validator, disassembler, interpreter, trace mode, profile mode, CLI, and importable library API.

**Package:** `python-pvm`  
**Import module:** `pvm`  
**Console script:** `pvm`  
**Python:** `>=3.10`  
**Runtime dependencies:** none  
**Core value types:** `int | bool`  
**Bytecode format:** `PVM1`  
**Coverage gate:** 95%

---

## System Context

```text
.asm source
  │
  ▼
two-pass assembler
  │
  ├── pass one: functions, labels, instruction offsets
  └── pass two: constants, label resolution, function indexes, code bytes
        │
        ▼
      Program
        │
        ├── serialize_program() -> PVM1 bytes
        ├── disassemble() -> assembly text
        ├── validate_program()
        └── VM.run()
```

---

## Package Layout

```text
src/pvm/
  __init__.py       # public API exports
  assembler.py      # two-pass assembly parser/emitter
  bytecode.py       # PVM1 serializer/deserializer
  cli.py            # argparse command-line interface
  disassembler.py   # Program -> assembly text
  errors.py         # public error hierarchy
  format.py         # canonical value formatting
  names.py          # identifier/entrypoint helpers
  opcodes.py        # opcode enum, specs, encode/decode helpers
  program.py        # Function and Program dataclasses
  validate.py       # defensive bytecode/program validation
  vm.py             # iterative execution engine
```

---

## Data Flow: Assemble

```text
assemble(source)
  ├── resolve entrypoint from argument or ; entrypoint directive
  ├── pass one
  │    ├── parse functions
  │    ├── validate arity/local counts
  │    ├── record labels
  │    ├── record instruction offsets
  │    └── require terminal HALT/RETURN/JUMP
  ├── validate entrypoint exists and has arity 0
  ├── collect and deduplicate constants
  ├── resolve operands
  │    ├── constants -> constant indexes
  │    ├── locals -> slot numbers
  │    ├── labels/numeric jumps -> byte offsets
  │    └── functions -> function table index + argc
  ├── encode_instruction()
  ├── build Program
  └── validate_program()
```

---

## Data Flow: Run

```text
run(input)
  ├── if .asm:
  │     └── assemble_file()
  ├── else:
  │     └── load_program() -> deserialize_program() -> validate_program()
  ├── VM(program).run()
  │     ├── validate_program()
  │     ├── create entry frame
  │     ├── while not halted
  │     │    ├── enforce max_steps
  │     │    ├── fetch instruction at frame.ip
  │     │    ├── advance frame.ip
  │     │    ├── dispatch opcode handler
  │     │    ├── update counters
  │     │    └── optional trace
  │     └── return result
```

---

## Core Data Structures

### `Value`

```python
Value = int | bool
```

Rules:
- assembly constants are signed 64-bit integers or booleans
- runtime arithmetic uses Python arbitrary-precision integers
- booleans are not accepted as integers

### `Function`

```python
@dataclass(slots=True)
class Function:
    name: str
    arity: int
    num_locals: int
    code: bytes
```

Purpose:
- stores one function's bytecode
- `arity` defines how many call arguments it receives
- `num_locals` defines local slot count
- `num_locals >= arity`

### `Program`

```python
@dataclass(slots=True)
class Program:
    constants: list[Value]
    functions: dict[str, Function]
    entrypoint: str = "main"
```

Purpose:
- in-memory executable representation
- maintains function table order
- maps function names to `Function`
- records entry function

### `VMConfig`

```python
@dataclass(slots=True)
class VMConfig:
    max_stack_depth: int = 1024
    max_call_depth: int = 256
    max_steps: int = 10_000_000
```

Purpose:
- bounds operand-stack growth
- bounds guest recursion
- bounds infinite loops
- `max_steps=0` disables step limit and prints a warning

### `Frame`

```python
@dataclass(slots=True)
class Frame:
    function_name: str
    ip: int
    locals: list[Value | None]
    stack: list[Value]
```

Purpose:
- one guest call frame
- owns its own instruction pointer
- owns local slots
- owns operand stack
- no Python recursion needed

---

## ISA

### Stack and constants

| Opcode | Operand bytes | Meaning |
|---|---:|---|
| `LOAD_CONST` | `u16` | Push constant pool value |
| `POP` | none | Discard top |
| `DUP` | none | Duplicate top |
| `SWAP` | none | Swap top two values |

### Arithmetic

| Opcode | Meaning |
|---|---|
| `ADD` | integer addition |
| `SUB` | integer subtraction |
| `MUL` | integer multiplication |
| `DIV` | integer division, truncating toward zero |
| `MOD` | remainder matching truncating division |
| `NEG` | integer negation |

### Comparison and boolean logic

| Opcode | Meaning |
|---|---|
| `EQ` / `NE` | equality/inequality on same exact type |
| `LT` / `LE` / `GT` / `GE` | integer ordering |
| `AND` / `OR` / `NOT` | boolean logic |

### Locals

| Opcode | Operand bytes | Meaning |
|---|---:|---|
| `LOAD_VAR` | `u8` | Push local slot |
| `STORE_VAR` | `u8` | Pop into local slot |

### Control flow

| Opcode | Operand bytes | Meaning |
|---|---:|---|
| `JUMP` | `u16` | Set IP to instruction boundary |
| `JUMP_IF_FALSE` | `u16` | Pop bool and jump when false |
| `JUMP_IF_TRUE` | `u16` | Pop bool and jump when true |

### Calls and termination

| Opcode | Operand bytes | Meaning |
|---|---:|---|
| `CALL` | `u16 function_index`, `u8 argc` | Push callee frame |
| `RETURN` | none | Return value to caller or finish program |
| `PRINT` | none | Pop and output value |
| `HALT` | none | Stop VM |

---

## Bytecode Encoding

### Instruction encoding

```text
opcode:u8 | fixed-width operands...
```

Operand widths:
- constant index: `u16`
- jump target: `u16`
- local slot: `u8`
- function table index: `u16`
- argc: `u8`

### File format

```text
"PVM1"
version:u8
entrypoint:text

constant_count:u16
constants...

function_count:u16
functions...
```

Text:
```text
byte_length:u16 | UTF-8 bytes
```

Constant:
```text
type:u8 | bool:u8 OR signed_integer:i64
```

Function:
```text
name:text | arity:u8 | locals:u8 | code_length:u32 | code
```

Limits:
- 65,535 constants
- 65,535 functions
- text field length <= 65,535 bytes
- function arity <= 255
- local count <= 255

---

## Validation

`validate_program()` checks:
- object is a `Program`
- program has functions
- entrypoint exists
- entrypoint name is a valid ASCII identifier
- entrypoint arity is zero
- constants are exact `int` or `bool`
- serialized int constants fit signed 64-bit range
- function table key matches function name
- function names are valid ASCII identifiers
- arity and local counts are valid
- locals are not fewer than arguments
- function code is non-empty bytes
- opcodes are known
- operands are not truncated
- constant indexes are in range
- local slots are in range
- jump targets land on instruction boundaries
- function indexes are in range
- `CALL` argc matches callee arity
- functions end with `HALT`, `RETURN`, or `JUMP`

Not checked statically:
- stack underflow
- stack overflow
- type mismatch
- divide by zero
- uninitialized local reads
- infinite loops

Those remain runtime VM errors.

---

## VM Execution Engine

The VM:
- validates the program at run start
- creates an entry frame
- loops until halted
- decodes instruction at current frame IP
- advances IP before executing
- table-dispatches the opcode
- updates instruction/opcode counters
- records max stack depth and max call depth
- optionally emits trace lines

### Call behavior

`CALL`:
1. verifies target function index and argc
2. pops arguments from caller stack in push order
3. creates callee locals list
4. places first pushed argument into local slot `0`
5. appends a new frame

`RETURN`:
1. pops result from callee stack
2. removes callee frame
3. if no caller remains, sets VM result and halts
4. otherwise pushes result to caller stack

### Halt behavior

`HALT`:
- if current operand stack has a value, VM result becomes top value
- otherwise result is `None`
- stack is not popped

---

## Trace and Profile

Trace output contains:
- function name
- pre-execution instruction pointer
- opcode
- encoded operands
- post-execution stack for the frame that ran
- post-execution locals for that frame
- call depth at execution time

`pvm profile` runs the program and reports:
- total instructions retired
- max stack depth
- max call depth
- opcode execution counts

CLI trace/profile telemetry is written to stderr so program stdout remains clean.

---

## Known Limits

- Values are integers and booleans only.
- No strings as VM values.
- No heap.
- No objects.
- No arrays.
- No closures.
- No garbage collection.
- No modules.
- No threads.
- No source-language compiler.
- No debug metadata in bytecode.
- No static stack-sufficiency analysis.
- No interactive debugger.
- No control-flow graph tool yet.

---

## Verification Summary

The repository configures:
- Python 3.10+
- zero runtime dependencies
- pytest
- coverage over `pvm`
- coverage fail-under 95
- strict mypy over `src/pvm`
- Ruff lint and format checks
- CI across Python 3.10, 3.11, 3.12, 3.13, and 3.14
- example smoke test: assemble factorial, validate bytecode, run and expect `120`

README states:
- 23 test modules
- 387 tests
- tests cover assembler, bytecode, CLI, disassembler, errors, format, names, opcodes, program model, validation, VM handlers, and example programs

---

*Constitution reference: Article 4 (engineering quality), Article 6 (behavior verification), Article 7 (progressive complexity), and Article 8 (valid learner work).*

---


# Interface Design Specification
## App — Virtual Machine
**Bytecode Runtime Systems Group | Document 3 of 5**

---

## Public CLI Interface

### Console command

```powershell
pvm <command> [options]
```

Equivalent module form:

```powershell
python -m pvm <command> [options]
```

---

## Global Options

| Option | Meaning |
|---|---|
| `--version` | Print package version |
| `--debug` | Re-raise expected `PVMError` exceptions with full traceback |

`--debug` must appear before the subcommand:

```powershell
pvm --debug run program.bc
```

---

## Commands

### `assemble`

```powershell
pvm assemble examples/factorial.asm -o factorial.bc
pvm assemble program.asm -o program.bc --entrypoint boot
```

Behavior:
- reads UTF-8 / UTF-8 with BOM assembly source
- builds `Program`
- validates it
- writes `PVM1` bytecode
- prints assembled function count

### `run`

```powershell
pvm run factorial.bc
pvm run examples/factorial.asm --trace
pvm run program.asm --entrypoint boot
```

Behavior:
- `.asm` input is assembled first
- bytecode input is loaded and validated
- runs the program
- prints program output to stdout
- trace output goes to stderr

### `disasm`

```powershell
pvm disasm factorial.bc
pvm disasm program.asm
```

Behavior:
- renders validated program as readable assembly
- emits a leading `; entrypoint <name>` comment
- creates synthetic labels for jump targets

### `validate`

```powershell
pvm validate factorial.bc
pvm validate examples/factorial.asm
```

Behavior:
- validates structure and bytecode semantics
- prints `Valid PVM1 program: <n> function(s), <m> constant(s)`

### `profile`

```powershell
pvm profile factorial.bc
pvm profile factorial.bc --trace
```

Behavior:
- runs the program
- program stdout remains stdout
- profile stats go to stderr

---

## Assembly Interface

### Function declaration

```asm
func <name> <arity> <num_locals>
```

Rules:
- function names must be valid ASCII identifiers
- arity/local counts are 0..255
- local count must be at least arity
- functions must contain at least one instruction
- functions must end with `HALT`, `RETURN`, or `JUMP`

### Entrypoint directive

```asm
; entrypoint boot
```

Rules:
- appears before first function
- must name an existing function
- entrypoint must have arity 0
- CLI `--entrypoint` overrides the source directive for `.asm` input

### Labels

```asm
loop:
    LOAD_VAR 0
    JUMP_IF_FALSE end
    JUMP loop
end:
    HALT
```

Rules:
- labels are scoped to a function
- jump targets must land on instruction boundaries
- synthetic labels from disassembly look like `L0004`

### Comments

Supported comment markers:

```text
;
#
//
```

### Constants

`LOAD_CONST` accepts:
- `true`
- `false`
- decimal integer
- `0x` hex
- `0o` octal
- `0b` binary

Rules:
- decimal integers cannot carry leading zero
- stored constants must fit signed 64-bit range
- bools and ints are distinct

---

## Instruction Reference

| Instruction | Operands | Stack effect |
|---|---|---|
| `LOAD_CONST` | literal | `[] -> [value]` |
| `POP` | — | `[x] -> []` |
| `DUP` | — | `[x] -> [x, x]` |
| `SWAP` | — | `[a, b] -> [b, a]` |
| `ADD` | — | `[int, int] -> [int]` |
| `SUB` | — | `[int, int] -> [int]` |
| `MUL` | — | `[int, int] -> [int]` |
| `DIV` | — | `[int, int] -> [int]` |
| `MOD` | — | `[int, int] -> [int]` |
| `NEG` | — | `[int] -> [int]` |
| `EQ` | — | `[T, T] -> [bool]` |
| `NE` | — | `[T, T] -> [bool]` |
| `LT` | — | `[int, int] -> [bool]` |
| `LE` | — | `[int, int] -> [bool]` |
| `GT` | — | `[int, int] -> [bool]` |
| `GE` | — | `[int, int] -> [bool]` |
| `AND` | — | `[bool, bool] -> [bool]` |
| `OR` | — | `[bool, bool] -> [bool]` |
| `NOT` | — | `[bool] -> [bool]` |
| `LOAD_VAR` | slot | `[] -> [value]` |
| `STORE_VAR` | slot | `[value] -> []` |
| `JUMP` | label/offset | unchanged |
| `JUMP_IF_FALSE` | label/offset | `[bool] -> []` |
| `JUMP_IF_TRUE` | label/offset | `[bool] -> []` |
| `CALL` | function argc | `[args...] -> [result]` |
| `RETURN` | — | `[result] -> caller` |
| `PRINT` | — | `[value] -> []` |
| `HALT` | — | unchanged |

---

## Bytecode Interface

### File layout

```text
"PVM1" | version:u8 | entrypoint:text
constant_count:u16 | constants...
function_count:u16 | functions...
```

### Text field

```text
byte_length:u16 | UTF-8 bytes
```

### Constant field

```text
type:u8 | bool:u8 OR signed_integer:i64
```

### Function field

```text
name:text | arity:u8 | locals:u8 | code_length:u32 | code
```

---

## Public Python API

Common imports:

```python
import pvm

program = pvm.assemble("""
func main 0 0
    LOAD_CONST 6
    PRINT
    HALT
""")

pvm.VM(program, output=lambda value: print(pvm.format_value(value))).run()
blob = pvm.serialize_program(program)
restored = pvm.deserialize_program(blob)
print(pvm.disassemble(restored))
```

Exported API includes:
- `assemble`
- `assemble_file`
- `serialize_program`
- `deserialize_program`
- `load_program`
- `save_program`
- `disassemble`
- `validate_program`
- `VM`
- `VMConfig`
- `Program`
- `Function`
- `format_value`
- full `PVMError` hierarchy

---

## Runtime Limits Interface

```python
pvm.VM(
    program,
    config=pvm.VMConfig(
        max_stack_depth=1024,
        max_call_depth=256,
        max_steps=10_000_000,
    ),
).run()
```

Rules:
- stack/call limits must be positive
- `max_steps` cannot be negative
- `max_steps=0` disables step limit and warns to stderr

---

## Output Contract

`PRINT`:
- pops top value
- writes via configured output callback
- CLI prints ints as decimal
- CLI prints booleans as lowercase `true` / `false`

`HALT`:
- stops without popping
- VM result is top stack value if present, else `None`

`RETURN`:
- pops result
- returns it to caller stack
- returning from final frame sets `VM.run()` result

---

## Exit Codes

| Code | Meaning |
|---:|---|
| `0` | Success |
| `1` | Expected PVM failure |
| `2` | argparse usage error |
| other | unexpected Python/runtime failure when using debug or uncaught errors |

---

*Constitution reference: Article 4 (input/output boundaries), Article 6 (verification), and Article 8 (understandable and verifiable work).*

---


# Runbook
## App — Virtual Machine
**Bytecode Runtime Systems Group | Document 4 of 5**

---

## Requirements

### Runtime

- Python 3.10+
- No runtime dependencies

### Development

- pytest
- pytest-cov
- ruff
- mypy
- pre-commit

---

## Installation

### Runtime-only

```powershell
python -m pip install -r requirements.txt
```

### Development

```powershell
python -m pip install -r requirements-dev.txt
pre-commit install
```

### Editable install

```powershell
python -m pip install -e .
python -m pip install -e ".[dev]"
```

---

## First Smoke Test

```powershell
python -m pvm --version
python -m pvm assemble examples/factorial.asm -o factorial.bc
python -m pvm validate factorial.bc
python -m pvm run factorial.bc
```

Expected output from run:

```text
120
```

---

## Run From Assembly

```powershell
python -m pvm run examples/arithmetic.asm
python -m pvm run examples/loop.asm
python -m pvm run examples/fibonacci.asm
```

Expected examples:
- arithmetic prints `14`
- loop prints `15`
- factorial prints `120`
- fibonacci prints `55`

---

## Trace Execution

```powershell
python -m pvm run examples/factorial.asm --trace
```

Expected:
- program output remains stdout
- trace lines go to stderr
- each line includes function, IP, opcode, operands, stack, locals, and depth

---

## Profile Execution

```powershell
python -m pvm profile factorial.bc
```

Expected:
- program output on stdout
- stats on stderr:
  - instructions
  - max stack depth
  - max call depth
  - opcode counts

---

## Disassemble

```powershell
python -m pvm disasm factorial.bc
```

Expected:
- assembly text
- `; entrypoint <name>` comment
- synthetic labels for jump targets
- byte offsets in comments

---

## Validate

```powershell
python -m pvm validate factorial.bc
```

Expected:

```text
Valid PVM1 program: 2 function(s), 2 constant(s)
```

---

## Entrypoint

Assembly:

```asm
; entrypoint boot
func boot 0 0
    LOAD_CONST 1
    PRINT
    HALT
```

CLI override:

```powershell
python -m pvm run program.asm --entrypoint boot
```

Note:
- `--entrypoint` applies only to `.asm`
- `.bc` files carry their own entrypoint

---

## Failure Demos

### Bad jump

```powershell
python -m pvm assemble examples/bad_jump.asm -o bad.bc
```

Expected:
- assembler/validator rejection

### Stack underflow

```powershell
python -m pvm run examples/bad_stack_underflow.asm
```

Expected:
- runtime `StackUnderflowError`

### Division by zero

```powershell
python -m pvm run examples/bad_div_zero.asm
```

Expected:

```text
error: division by zero (function=main, ip=6, opcode=DIV)
```

---

## Library Smoke Test

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

pvm.VM(program, output=lambda value: print(pvm.format_value(value))).run()
blob = pvm.serialize_program(program)
restored = pvm.deserialize_program(blob)
print(pvm.disassemble(restored))
```

Expected:
- prints `36`
- serializes/deserializes valid bytecode
- disassembles readable assembly

---

## Quality Checks

### Ruff

```powershell
python -m ruff check src tests
python -m ruff format --check src tests
```

### Mypy

```powershell
python -m mypy
```

### Tests and coverage

```powershell
python -m pytest --cov=pvm --cov-report=term-missing --cov-fail-under=95
```

---

## CI Parity

GitHub Actions runs:
- Ubuntu latest
- Python 3.10, 3.11, 3.12, 3.13, and 3.14
- install package and dev tooling
- Ruff check
- Ruff format check
- mypy
- pytest with coverage gate 95
- factorial smoke test:
  - assemble
  - validate
  - run and expect `120`

---

## Troubleshooting

### `error: entrypoint 'main' does not exist`

Cause:
- program lacks `main`
- no `; entrypoint` directive
- no CLI `--entrypoint`

Fix:

```powershell
python -m pvm run program.asm --entrypoint boot
```

---

### `jump target ... is not an instruction boundary`

Cause:
- numeric jump target points into operand bytes or past code
- label resolution produced invalid target

Fix:
- use labels rather than numeric offsets where possible
- inspect with `disasm` after successful assembly

---

### `operand stack underflow`

Cause:
- instruction needed a value that was not on the frame stack

Fix:
- inspect instruction order
- run with `--trace`

---

### `expected integer, got bool`

Cause:
- arithmetic/order op received boolean

Fix:
- keep integer and boolean paths separate

---

### `local slot ... is uninitialized`

Cause:
- `LOAD_VAR` used before `STORE_VAR` or before argument assignment

Fix:
- initialize the local before load
- verify function arity/local layout

---

### `step limit ... exceeded`

Cause:
- likely infinite loop

Fix:
- run with `--trace`
- inspect jump conditions
- raise `max_steps` only intentionally through library config

---

## Maintenance Notes

- Keep assembler/bytecode/validator/VM separation.
- Keep bytecode validation defensive.
- Do not use Python recursion for guest calls.
- Add tests before changing opcode encodings.
- Add tests before changing division/modulo semantics.
- Add tests before changing entrypoint behavior.
- Add tests before changing bytecode format.
- Preserve `PVM1` versioning.
- Preserve CLI stderr/stdout separation for trace/profile.
- Preserve strict bool/int separation.
- Add an ADR before adding heap, objects, debugger, source compiler, or visual UI.

---

*Constitution reference: Article 6 (behavior verification), Article 5 (constraints and trade-offs), and Article 8 (verifiable learner work).*

---


# Lessons Learned
## App — Virtual Machine
**Bytecode Runtime Systems Group | Document 5 of 5**

---

## Why This Design Was Chosen

This design was chosen because a virtual machine is one of the clearest ways to show systems thinking in Python. The project demonstrates the full runtime pipeline: assembly text, bytecode encoding, validation, disassembly, instruction dispatch, stack behavior, local slots, function calls, runtime errors, and execution limits.

The stack-machine model was the right scope. It is compact enough to audit instruction by instruction but expressive enough to run loops, branches, recursion, factorial, and Fibonacci. A register VM would be valuable later, but it would make the first version larger without changing the core learning objective.

The most important design boundary is validation. The assembler emits valid programs, but the VM and loader still treat bytecode as untrusted. That makes the system safer and easier to explain.

---

## What Was Intentionally Omitted

**High-level compiler:** Out of scope.

**Objects/heap/GC:** Deferred.

**Strings as VM values:** Deferred.

**Arrays/maps:** Deferred.

**Modules/imports:** Deferred.

**Threads/concurrency:** Out of scope.

**JIT compilation:** Out of scope.

**Interactive debugger:** Deferred.

**Static stack analysis:** Deferred.

**Control-flow graph reporting:** Deferred.

**Debug metadata in bytecode:** Deferred.

**Django/HTMX visual stepper:** Future stretch only.

---

## Biggest Weakness

The biggest weakness is that validation does not prove stack safety. Invalid stack behavior is caught at runtime through clear VM errors, but a stronger VM could statically verify stack effects across every branch and function before execution.

The second weakness is the limited value model. Integers and booleans are enough for the current instruction set, but future programs would quickly want strings, arrays, objects, or heap-allocated structures.

The third weakness is that bytecode carries no debug metadata. Errors report function, IP, and opcode, but not source line numbers.

---

## Scaling Considerations

**If the VM grows:**
- add a heap model
- add strings/arrays
- add bytecode debug metadata
- add source-line maps
- add a debugger
- add bytecode digesting
- add control-flow graph reporting

**If validation grows:**
- perform static stack-depth analysis
- verify branch stack consistency
- verify every function return path
- detect unreachable code
- calculate maximum stack depth before execution

**If performance grows:**
- pre-decode functions into instruction objects
- reduce repeated decode work
- benchmark table dispatch vs match/case
- keep semantics identical before optimizing

**If language support grows:**
- create a tiny compiler as a separate project layer
- keep assembler as the stable low-level representation
- keep `PVM1` backward compatibility or bump version deliberately

---

## What the Next Refactor Would Be

1. **Static stack verifier** — reject underflow and inconsistent branch stack shapes before runtime.

2. **Predecoded bytecode** — decode each function once after validation for faster execution.

3. **Debug metadata** — optionally map bytecode offsets back to assembly source lines.

4. **Interactive debugger** — step, breakpoints, frame inspection, and stack/local display.

5. **Control-flow graph tool** — visualize branches, loops, and unreachable code.

---

## What This Project Taught

- **A VM is a contract between bytecode and runtime.** The instruction set, operand widths, validation rules, and runtime semantics must agree exactly.

- **Validation is a boundary.** Every bytecode file should be treated as hostile until proven structurally safe.

- **Stacks simplify instruction encoding.** Arithmetic instructions do not need register operands, but they require disciplined stack effects.

- **Guest recursion should not use host recursion.** VM-owned frames make call depth explicit and bounded.

- **Type systems matter even in tiny VMs.** Python's `bool`/`int` relationship cannot leak into VM semantics.

- **Trace and profile make a VM teachable.** Execution is easier to trust when each instruction can be observed.

- **Small formats need limits.** Fixed-width operands make decoding simple, but table sizes and text lengths need clear caps.

- **Scope discipline produces a stronger project.** A focused VM is more defensible than an unfocused attempt at a complete programming language.

---

*Constitution v2.0 checklist: This document satisfies Article 5 (trade-off documentation), Article 6 (verification), and Article 7 (progressive complexity) for Virtual Machine.*
