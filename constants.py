GET_MODEL_RESPONSE = 1
COMPILE_CODE = 2
TEST_CODE = 3
UPDATE_QUESTION_DESCRIPTION = 4

INITIAL_MESSAGE = ("You are an expert Python code developer. Understand what the question asks and write an executable Python"
                   " code for the given problem. Write the code in one function only. You need to only provide the code "
                   "output and no explanation, comments, markdown, code fence, etc are needed. Declare function variables as "
                   "stated in the question and in the same order. Do not enclose the response in ```python. Do not use "
                   "variable names like time, os or other existing python module names.")

NO_SOLUTION = "LLM produced no solution. Can you try again and generate a python solution for the given problem? "

SAVE_ERROR = "Could not save code. Can you modify the code as per the following error: "

SYNTAX_ERROR = "The previous solution failed to compile. Can you please generate a solution that executes."

COMPILE_TIME_ERROR = "Code could not be compiled within and was terminated. Possibly due to an infinite loop or order of the results. Please modify the code accordingly."

FUNCTION_ERROR = ("Please modify the code. No function found in the solution. You should return a code with a function written in "
                    "Python that solves the problem.")