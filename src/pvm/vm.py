"""Iterative fetch-decode-execute engine for PVM bytecode."""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from .errors import (
    CallDepthError,
    DivisionByZeroError,
    InvalidCallError,
    InvalidJumpError,
    StackOverflowError,
    StackUnderflowError,
    StepLimitError,
    TypeMismatchError,
    UninitializedLocalError,
    VMError,
)
from .opcodes import OpCode, decode_instruction, iter_instructions
from .program import Program, Value
from .validate import validate_program

OutputFunction = Callable[[object], None]


@dataclass(slots=True)
class VMConfig:
    max_stack_depth: int = 1024
    max_call_depth: int = 256
    # Bounds total executed instructions so infinite loops cannot hang the VM.
    # Set to 0 to disable. The default is far above any realistic program.
    max_steps: int = 10_000_000


@dataclass(slots=True)
class Frame:
    function_name: str
    ip: int
    locals: list[Value | None]
    stack: list[Value] = field(default_factory=list)


class VM:
    """Execute a validated Program without using Python recursion."""

    def __init__(
        self,
        program: Program,
        *,
        config: VMConfig | None = None,
        output: OutputFunction = print,
        trace: bool = False,
        trace_output: OutputFunction | None = None,
    ) -> None:
        self.program = program
        self.config = config or VMConfig()
        self.output = output
        self.trace_enabled = trace
        if trace_output is not None:
            self.trace_output = trace_output
        elif trace:
            self.trace_output = lambda line: print(line, file=sys.stderr)
        else:
            self.trace_output = output
        self.frames: list[Frame] = []
        self.halted = False
        self.result: Value | None = None
        self.instruction_count = 0
        self.max_stack_seen = 0
        self.max_call_depth_seen = 0
        self.opcode_counts: Counter[OpCode] = Counter()
        self._instruction_boundaries: dict[str, set[int]] = {}
        self._current_ip = 0
        self._current_opcode: OpCode | None = None
        self._handlers: dict[OpCode, Callable[[tuple[int, ...]], None]] = {
            OpCode.LOAD_CONST: self._op_load_const,
            OpCode.POP: self._op_pop,
            OpCode.DUP: self._op_dup,
            OpCode.SWAP: self._op_swap,
            OpCode.ADD: self._op_add,
            OpCode.SUB: self._op_sub,
            OpCode.MUL: self._op_mul,
            OpCode.DIV: self._op_div,
            OpCode.MOD: self._op_mod,
            OpCode.NEG: self._op_neg,
            OpCode.EQ: self._op_eq,
            OpCode.NE: self._op_ne,
            OpCode.LT: self._op_lt,
            OpCode.LE: self._op_le,
            OpCode.GT: self._op_gt,
            OpCode.GE: self._op_ge,
            OpCode.AND: self._op_and,
            OpCode.OR: self._op_or,
            OpCode.NOT: self._op_not,
            OpCode.LOAD_VAR: self._op_load_var,
            OpCode.STORE_VAR: self._op_store_var,
            OpCode.JUMP: self._op_jump,
            OpCode.JUMP_IF_FALSE: self._op_jump_if_false,
            OpCode.JUMP_IF_TRUE: self._op_jump_if_true,
            OpCode.CALL: self._op_call,
            OpCode.RETURN: self._op_return,
            OpCode.PRINT: self._op_print,
            OpCode.HALT: self._op_halt,
        }

    @property
    def frame(self) -> Frame:
        if not self.frames:
            raise VMError("the VM has no active frame")
        return self.frames[-1]

    def run(self) -> Value | None:
        # Bytecode is treated as untrusted, so it is validated before every
        # execution even when the assembler or loader just validated it.
        validate_program(self.program)
        if self.config.max_stack_depth <= 0 or self.config.max_call_depth <= 0:
            raise VMError("VM limits must be positive")
        if self.config.max_steps < 0:
            raise VMError("max_steps cannot be negative")
        if self.config.max_steps == 0:
            print(
                "warning: max_steps is 0; infinite loops will not be stopped",
                file=sys.stderr,
            )

        entry = self.program.functions[self.program.entrypoint]
        self.frames = [Frame(entry.name, 0, [None] * entry.num_locals)]
        self.halted = False
        self.result = None
        self.instruction_count = 0
        self.max_stack_seen = 0
        self.max_call_depth_seen = 1
        self.opcode_counts = Counter()
        self._instruction_boundaries = {
            function.name: {
                offset for offset, _, _, _ in iter_instructions(function.code)
            }
            for function in self.program.functions.values()
        }

        while not self.halted:
            if (
                self.config.max_steps
                and self.instruction_count >= self.config.max_steps
            ):
                raise self._error(
                    f"step limit {self.config.max_steps} exceeded",
                    StepLimitError,
                )
            executed_frame = self.frame
            function = self.program.functions[executed_frame.function_name]
            if executed_frame.ip >= len(function.code):
                self._current_ip = executed_frame.ip
                self._current_opcode = None
                raise self._error("instruction pointer ran past the function")
            ip = executed_frame.ip
            opcode, operands, size = decode_instruction(function.code, ip)
            self._current_ip = ip
            self._current_opcode = opcode
            executed_frame.ip += size
            depth = len(self.frames)
            handler = self._handlers[opcode]
            handler(operands)
            self.instruction_count += 1
            self.opcode_counts[opcode] += 1
            if self.trace_enabled:
                self._trace(executed_frame, ip, opcode, operands, depth)
        return self.result

    def _error(self, message: str, cls: type[VMError] = VMError) -> VMError:
        function = self.frames[-1].function_name if self.frames else None
        return cls(
            message,
            function=function,
            ip=self._current_ip,
            opcode=self._current_opcode.name if self._current_opcode else None,
        )

    def _trace(
        self,
        frame: Frame,
        ip: int,
        opcode: OpCode,
        operands: tuple[int, ...],
        depth: int,
    ) -> None:
        # fn / stack / locals / depth all describe the frame that ran this
        # instruction, captured just after it executed. CALL and RETURN move a
        # value across frames; that is visible by reading the adjacent lines.
        rendered_operands = " ".join(str(value) for value in operands) or "-"
        self.trace_output(
            f"TRACE fn={frame.function_name} ip={ip:04x} "
            f"op={opcode.name} args={rendered_operands} "
            f"stack={frame.stack!r} locals={frame.locals!r} "
            f"depth={depth}"
        )

    def _push(self, value: Value) -> None:
        if len(self.frame.stack) >= self.config.max_stack_depth:
            raise self._error(
                f"operand stack limit {self.config.max_stack_depth} exceeded",
                StackOverflowError,
            )
        self.frame.stack.append(value)
        self.max_stack_seen = max(self.max_stack_seen, len(self.frame.stack))

    def _pop(self) -> Value:
        if not self.frame.stack:
            raise self._error("operand stack underflow", StackUnderflowError)
        return self.frame.stack.pop()

    def _pop_two(self) -> tuple[Value, Value]:
        if len(self.frame.stack) < 2:
            raise self._error("operand stack needs two values", StackUnderflowError)
        right = self.frame.stack.pop()
        left = self.frame.stack.pop()
        return left, right

    def _require_int(self, value: Value) -> int:
        if type(value) is not int:
            raise self._error(
                f"expected integer, got {type(value).__name__}", TypeMismatchError
            )
        return value

    def _require_bool(self, value: Value) -> bool:
        if type(value) is not bool:
            raise self._error(
                f"expected boolean, got {type(value).__name__}", TypeMismatchError
            )
        return value

    def _int_pair(self) -> tuple[int, int]:
        left, right = self._pop_two()
        return self._require_int(left), self._require_int(right)

    def _bool_pair(self) -> tuple[bool, bool]:
        left, right = self._pop_two()
        return self._require_bool(left), self._require_bool(right)

    def _same_type_pair(self) -> tuple[Value, Value]:
        left, right = self._pop_two()
        if type(left) is not type(right):
            raise self._error(
                f"cannot compare {type(left).__name__} and " f"{type(right).__name__}",
                TypeMismatchError,
            )
        return left, right

    def _op_load_const(self, operands: tuple[int, ...]) -> None:
        self._push(self.program.constants[operands[0]])

    def _op_pop(self, operands: tuple[int, ...]) -> None:
        self._pop()

    def _op_dup(self, operands: tuple[int, ...]) -> None:
        if not self.frame.stack:
            raise self._error("operand stack underflow", StackUnderflowError)
        self._push(self.frame.stack[-1])

    def _op_swap(self, operands: tuple[int, ...]) -> None:
        if len(self.frame.stack) < 2:
            raise self._error("operand stack needs two values", StackUnderflowError)
        self.frame.stack[-2], self.frame.stack[-1] = (
            self.frame.stack[-1],
            self.frame.stack[-2],
        )

    def _op_add(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left + right)

    def _op_sub(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left - right)

    def _op_mul(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left * right)

    @staticmethod
    def _trunc_div(left: int, right: int) -> int:
        quotient = abs(left) // abs(right)
        return -quotient if (left < 0) != (right < 0) else quotient

    def _op_div(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        if right == 0:
            raise self._error("division by zero", DivisionByZeroError)
        self._push(self._trunc_div(left, right))

    def _op_mod(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        if right == 0:
            raise self._error("modulo by zero", DivisionByZeroError)
        self._push(left - self._trunc_div(left, right) * right)

    def _op_neg(self, operands: tuple[int, ...]) -> None:
        self._push(-self._require_int(self._pop()))

    def _op_eq(self, operands: tuple[int, ...]) -> None:
        left, right = self._same_type_pair()
        self._push(left == right)

    def _op_ne(self, operands: tuple[int, ...]) -> None:
        left, right = self._same_type_pair()
        self._push(left != right)

    def _op_lt(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left < right)

    def _op_le(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left <= right)

    def _op_gt(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left > right)

    def _op_ge(self, operands: tuple[int, ...]) -> None:
        left, right = self._int_pair()
        self._push(left >= right)

    def _op_and(self, operands: tuple[int, ...]) -> None:
        left, right = self._bool_pair()
        self._push(left and right)

    def _op_or(self, operands: tuple[int, ...]) -> None:
        left, right = self._bool_pair()
        self._push(left or right)

    def _op_not(self, operands: tuple[int, ...]) -> None:
        self._push(not self._require_bool(self._pop()))

    def _op_load_var(self, operands: tuple[int, ...]) -> None:
        slot = operands[0]
        value = self.frame.locals[slot]
        if value is None:
            raise self._error(
                f"local slot {slot} is uninitialized", UninitializedLocalError
            )
        self._push(value)

    def _op_store_var(self, operands: tuple[int, ...]) -> None:
        self.frame.locals[operands[0]] = self._pop()

    def _set_ip(self, target: int) -> None:
        if target not in self._instruction_boundaries[self.frame.function_name]:
            raise self._error(
                f"jump target {target} is not an instruction boundary",
                InvalidJumpError,
            )
        self.frame.ip = target

    def _op_jump(self, operands: tuple[int, ...]) -> None:
        self._set_ip(operands[0])

    def _op_jump_if_false(self, operands: tuple[int, ...]) -> None:
        condition = self._require_bool(self._pop())
        if not condition:
            self._set_ip(operands[0])

    def _op_jump_if_true(self, operands: tuple[int, ...]) -> None:
        condition = self._require_bool(self._pop())
        if condition:
            self._set_ip(operands[0])

    def _op_call(self, operands: tuple[int, ...]) -> None:
        target_index, argc = operands
        try:
            target = self.program.function_by_index(target_index)
        except (IndexError, KeyError) as exc:
            raise self._error(
                f"function index {target_index} does not exist", InvalidCallError
            ) from exc
        if argc != target.arity:
            raise self._error(
                f"{target.name} expects {target.arity} argument(s), got {argc}",
                InvalidCallError,
            )
        if len(self.frame.stack) < argc:
            raise self._error(f"CALL needs {argc} argument(s)", StackUnderflowError)
        if len(self.frames) >= self.config.max_call_depth:
            raise self._error(
                f"call depth limit {self.config.max_call_depth} exceeded",
                CallDepthError,
            )
        args = self.frame.stack[-argc:] if argc else []
        if argc:
            del self.frame.stack[-argc:]
        locals_: list[Value | None] = [None] * target.num_locals
        locals_[:argc] = args
        # The caller's resume point is preserved by its own frame.ip, so no
        # separate return address is stored on the callee frame.
        self.frames.append(Frame(target.name, 0, locals_))
        self.max_call_depth_seen = max(self.max_call_depth_seen, len(self.frames))

    def _op_return(self, operands: tuple[int, ...]) -> None:
        value = self._pop()
        self.frames.pop()
        if not self.frames:
            self.result = value
            self.halted = True
            return
        self._push(value)

    def _op_print(self, operands: tuple[int, ...]) -> None:
        self.output(self._pop())

    def _op_halt(self, operands: tuple[int, ...]) -> None:
        self.result = self.frame.stack[-1] if self.frame.stack else None
        self.halted = True
