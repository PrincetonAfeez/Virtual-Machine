# ADR 0001: Separate assembler, bytecode validator, disassembler, and VM

## Status

Accepted

## Context

PVM accepts assembly source and serialized bytecode. Bytecode files should be
treated as untrusted input.

## Decision

Keep parsing, validation, disassembly, and execution in separate modules. The
assembler emits a `Program`, the serializer stores PVM1 bytecode, the validator
checks structure and semantics, and the VM only executes validated `Program`
values.

## Consequences

This keeps execution simpler and safer, makes bytecode validation reusable,
and allows disassembly to operate on validated bytecode. It adds some module
boundaries and repeated validation, but the clarity is worth it for a
systems-programming capstone.
