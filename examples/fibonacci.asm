; Recursive fibonacci(10), implemented with VM call frames. Prints 55.
func main 0 0
    LOAD_CONST 10
    CALL fibonacci 1
    PRINT
    HALT

func fibonacci 1 1
    LOAD_VAR 0
    LOAD_CONST 1
    LE
    JUMP_IF_FALSE recurse
    LOAD_VAR 0
    RETURN

recurse:
    LOAD_VAR 0
    LOAD_CONST 1
    SUB
    CALL fibonacci 1
    LOAD_VAR 0
    LOAD_CONST 2
    SUB
    CALL fibonacci 1
    ADD
    RETURN

