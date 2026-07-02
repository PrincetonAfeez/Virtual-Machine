"""In-memory program model."""

from __future__ import annotations

from dataclasses import dataclass, field

Value = int | bool


@dataclass(slots=True)
class Function:
    name: str
    arity: int
    num_locals: int
    code: bytes


@dataclass(slots=True)
class Program:
    constants: list[Value] = field(default_factory=list)
    functions: dict[str, Function] = field(default_factory=dict)
    entrypoint: str = "main"

    def function_names(self) -> list[str]:
        return list(self.functions)

    def function_by_index(self, index: int) -> Function:
        return self.functions[self.function_names()[index]]
