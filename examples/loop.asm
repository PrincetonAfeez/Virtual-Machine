; Sum 1 through 5 using local slots: slot 0 is i, slot 1 is total.
func main 0 2
    LOAD_CONST 1
    STORE_VAR 0
    LOAD_CONST 0
    STORE_VAR 1

loop:
    LOAD_VAR 0
    LOAD_CONST 5
    LE
    JUMP_IF_FALSE done

    LOAD_VAR 1
    LOAD_VAR 0
    ADD
    STORE_VAR 1

    LOAD_VAR 0
    LOAD_CONST 1
    ADD
    STORE_VAR 0
    JUMP loop

done:
    LOAD_VAR 1
    PRINT
    HALT

