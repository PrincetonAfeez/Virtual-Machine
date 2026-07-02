; Prints 100 because 7 is greater than 4.
func main 0 0
    LOAD_CONST 7
    LOAD_CONST 4
    GT
    JUMP_IF_FALSE else
    LOAD_CONST 100
    PRINT
    JUMP done

else:
    LOAD_CONST 200
    PRINT

done:
    HALT

