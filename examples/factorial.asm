; Recursive factorial(5), implemented with VM call frames. Prints 120.
func main 0 0
    LOAD_CONST 5
    CALL factorial 1
    PRINT
    HALT

func factorial 1 1
    LOAD_VAR 0
    LOAD_CONST 1
    LE
    JUMP_IF_FALSE recurse
    LOAD_CONST 1
    RETURN

recurse:
    LOAD_VAR 0
    LOAD_VAR 0
    LOAD_CONST 1
    SUB
    CALL factorial 1
    MUL
    RETURN

