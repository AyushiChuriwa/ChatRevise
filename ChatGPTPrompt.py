import time as time_module
import openai
import os as os_module
import pandas as pd
import itertools
from typing import Optional
from importsCheck import *
import testCaseParser
import constants
from func_timeout import func_timeout, FunctionTimedOut
import argparse

# Include the openAI key
openai.api_key = os_module.getenv("OPENAI_API_KEY")

questionName = []
questionDescription = []
testCasesList = [[]]
promptList = [[]]
tokenLengthPrompt = [[]]
errorList = [[]]
testsFailedList = [[]]
solved = []
iterationSolved = []
timeReq = [[]]
totalTimeReq = []

model = "gpt-3.5-turbo"
question_order = True


def printToTerminalFile(*args, **kwargs):
    """
    This function logs all statements to a file ChatGPTResponseOutput.

    """
    original_stdout = sys.stdout
    print(*args, **kwargs)
    try:
        file_name = "ResponseLog_" + model + ".txt"
        f = open(file_name, 'a', encoding="utf-8")
        sys.stdout = f
        print(*args, **kwargs)
        sys.stdout = original_stdout
        f.close()
    finally:
        sys.stdout = original_stdout


def resultCSV():
    """
    This function creates a csv file with the result analysis.

    """
    printToTerminalFile("writing results: ")
    csv_file_name = "ResponseList_" + model + ".csv"
    global questionName, questionDescription, testCasesList, promptList, errorList, testsFailedList, solved, iterationSolved
    printToTerminalFile(len(question_description), len(question_name), len(testCasesList), len(promptList),
                        len(errorList), len(testsFailedList), len(solved), len(iterationSolved))
    df = pd.DataFrame({
        'Question Name': questionName,
        'Question Description': questionDescription,
        'Test Cases': testCasesList,
        'Prompts Sent': promptList,
        'Token length of Prompts': tokenLengthPrompt,
        'Error': errorList,
        'Test Failed': testsFailedList,
        'ChatGPT solved': solved,
        'Iteration Solved/ Failed': iterationSolved,
        'Individual iteration time': timeReq,
        'Time Required To solve': totalTimeReq
    })
    printToTerminalFile(df)
    if os_module.path.exists(csv_file_name):
        printToTerminalFile("Appending Results to csv file")
        df.to_csv(csv_file_name, header=False, mode='a')

    else:
        printToTerminalFile("Creating csv file")
        df.to_csv(csv_file_name)

    questionName.clear()
    questionDescription.clear()
    testCasesList.clear()
    promptList.clear()
    tokenLengthPrompt.clear()
    errorList.clear()
    testsFailedList.clear()
    solved.clear()
    iterationSolved.clear()
    timeReq.clear()
    totalTimeReq.clear()

    testCasesList.append([])
    promptList.append([])
    tokenLengthPrompt.append([])
    errorList.append([])
    testsFailedList.append([])
    timeReq.append([])


def chat_with_chatgpt(message, model):
    """
    This function calls ChatGPT for a response solution for the given prompt.

    :param message: The prompt to send to ChatGPT
    :param model: ChatGPT model being used
    :return: ChatGPT generated solution
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=message,
        max_tokens=4096,
        temperature=1,
    )

    generated_output = response.choices[0].message.content.strip()
    printToTerminalFile("Model being used: ", response.model)

    #csv variable
    globals()['tokenLengthPrompt'][0].append(response.usage.prompt_tokens)
    return generated_output


def save_code(code, filename, version):
    """
    This function saves the responses generated by ChatGPT.

    :param code: The response to save
    :param filename: The question name to be saved as filename
    :param version: The feedback loop count
    :return: Boolean stating execution status
    """

    folder_name = filename.replace(" ", "").replace(":", "_").replace("?", "").replace("/", "_")
    file_name = folder_name + "_Solution_" + str(version) + '.py'

    current_directory = os_module.getcwd()
    path = "/Solutions_" + model + "/" + folder_name
    sol_path = os_module.path.join(current_directory + path)
    if_exists = os_module.path.exists(sol_path)

    if not if_exists:
        os_module.makedirs(sol_path)
    try:
        with open(sol_path + "/" + file_name, "w", encoding="utf-8") as file1:
            file1.writelines(code)
        printToTerminalFile("Solution saved successfully!")
        return True, None
    except Exception as e:
        printToTerminalFile(str(e))
        return False, str(e)


def compile_code(code):
    """
    This function tries to compile the generated solution and returns the error otherwise.

    :param code: The response to compile
    :return: String stating execution status
    """
    printToTerminalFile("Compiling code for :", fetch_function_name(code))

    try:
        return_value = func_timeout(10, exec, args=(code, globals()))
        printToTerminalFile("Executed code compile -------------")
    except FunctionTimedOut as fte:
        output = "Failed to compile!"
        feedback = "Code could not be compiled within 10 seconds and was terminated. Possibly due to an infinite loop. Please modify the code accordingly."
        printToTerminalFile(feedback)
        return output, feedback
    except Exception as e:
        printToTerminalFile("Exception occurred ----------------")
        output = "Failed to compile!"
        feedback = str(e)
        printToTerminalFile(str(e))
        return output, feedback

    return "Code compiled successfully!", None


def fetch_function_name(code) -> Optional[str]:
    """
    This function fetches the function name from a given code using its ast.

    :param code: The code containing the function
    :return: string stating the function name
    """
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name != "main":
            return node.name
    return None


def test_code(code, test_cases, question_description):
    """
    This function tests the response for any kind of error. It evaluates the code against the testcases and sends an appropriate feedback.

    :param code: The code to test
    :param test_cases: The test cases to evaluate the code
    :return: Boolean stating execution status
    :return: Failed test case number
    :return: feedback containing the error message
    """
    feedback = ""
    i = -1
    output_list = []
    # check for compilation error
    try:
        response, feedback = compile_code(code)
        if response != 'Failed to compile!':
            function_name = fetch_function_name(code)
            if function_name is None:
                feedback = ("Please modify the code. No function found in the solution. You should return a function in "
                            "Python that solves the problem.")
                return False, 0, feedback
            else:
                printToTerminalFile('Parsing test cases for function: ', function_name)
                test_cases = testCaseParser.parse_test_case(test_cases)

                #csv variable
                global testCasesList
                if len(globals()['testCasesList'][0]) == 0:
                    globals()['testCasesList'][0].append(test_cases)

                for i, test_case in enumerate(test_cases):
                    input = test_case['Input']
                    expected_output = test_case['Output']
                    returned_output = None

                    #Adding test cases to the question message
                    if feedback == "" or feedback is None:
                        feedback = f"Example test case {i + 1}: \n Input: {input} \n Output: {expected_output}"
                    else:
                        feedback += f"Example test case {i + 1}: \n Input: {input} \n Output: {expected_output}"

                    if isinstance(input, list):
                        returned_output = func_timeout(30, globals()[function_name], args=(*input,))
                    else:
                        returned_output = func_timeout(30, globals()[function_name], args=(input,))
                    printToTerminalFile(
                        f">> Input: {input}\n>> Output Returned: {returned_output}\n>> Output Expected: {expected_output}")

                    # Compare the output with the expected output as output stored/fetched from dataset is string not bool
                    if isinstance(returned_output, bool) and (expected_output == 'true' or expected_output == 'True'):
                        expected_output = True
                    elif isinstance(returned_output, bool) and (expected_output == 'false' or expected_output == 'False'):
                        expected_output = False

                    if returned_output != expected_output:
                        any_order = ["return the answer in any order", "return the solution in any order",
                                     "return the values in any order"]
                        if question_order and any(
                                order in question_description for order in any_order) and isinstance(returned_output, list):
                            # Can handle only simple permutations on the entire output not partially allowed permutations
                            permutated_returned_output = func_timeout(30, list(itertools.permutations), args=(returned_output,))
                            if expected_output in permutated_returned_output:
                                printToTerminalFile("Test case passed!\n")
                                output_list.append(returned_output)
                                break
                            else:
                                printToTerminalFile("Output returned is not as expected! Modifying the prompt.\n")
                                feedback += (
                                    f" Please modify the code. Use different concepts or change small segments of the "
                                    f"generated code to make it satisfy all test cases. The previous solution gives "
                                    f"incorrect results against the following test case. \nTest case {i + 1} failed: "
                                    f"Expected output: {expected_output} but output returned is: {returned_output}")
                                printToTerminalFile(feedback)
                                return False, i + 1, feedback
                        else:
                            printToTerminalFile("Output returned is not as expected! Modifying the prompt.\n")
                            feedback += (f" Please modify the code. Use different concepts or change small segments of the "
                                         f"generated code to make it satisfy all test cases. The previous solution gives "
                                         f"incorrect results against the following test case. \nTest case {i + 1} failed: "
                                         f"Expected output: {expected_output} but output returned is: {returned_output}")
                            printToTerminalFile(feedback)
                            return False, i + 1, feedback
                    else:
                        printToTerminalFile("Test case passed!\n")
                        output_list.append(returned_output)

                # All test cases passed
                if len(output_list) == len(test_cases):
                    return True, 0, None
        else:
            feedback += "The previous solution failed to compile. Can you please generate a solution that executes."

    except FunctionTimedOut as fte:
        feedback = "Code could not be compiled within 30 seconds and was terminated. Possibly due to an infinite loop or order of the results. Please modify the code accordingly."
        printToTerminalFile(feedback)
        return False, i + 1, feedback
    except Exception as e:
        feedback += f"Please modify the code. The previous solution gives the following error: \n {str(e)}"
        return False, i + 1, feedback
    return False, 0, feedback


def fetch_question_details(excel_file_name, start=0):
    """
    This function reads the LeetCode file and fetches the data.

    :param excel_file_name: The file to read
    :param start: The starting index of the question
    :return: question names of LeetCode problems
    :return: question descriptions of LeetCode
    :return: test cases of LeetCode problems
    """
    excel_file_path = excel_file_name
    question_names = []
    question_descriptions = []
    test_cases = []

    if os_module.path.exists(excel_file_path):
        printToTerminalFile("Fetching question details...")
        df = pd.read_excel(excel_file_path)
        all_rows = df.values.tolist()

        for question in range(start, len(all_rows)):
            # ensure question_names, question_descriptions, test_cases are not null
            # ensure it is not a premium question and that there is at least 1 test case available
            #ensure the answer is not asking for results in any order
            if (all_rows[question][0] and all_rows[question][5] and all_rows[question][7]
                    and (
                            'in any order' not in str(all_rows[question][5]) if question_order is False else True)
                    and all_rows[question][2] != "Yes" and all_rows[question][6] > 0):
                question_names.append(all_rows[question][0])
                question_descriptions.append(all_rows[question][5])
                test_cases.append(all_rows[question][7])
    else:
        printToTerminalFile("Could not find question details file path!")
    print("Finished fetched ", len(question_names), " questions.\n")
    return question_names, question_descriptions, test_cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model selection.")
    parser.add_argument("model", help="The OpenAI model to query")
    parser.add_argument("-q", "--questions_file", help="Questions to test")
    parser.add_argument("-o", "--order", action="store_true", help="Test questions which return solutions in any order")
    parser.add_argument("-s", "--start", type=int, help="Question number to start with")  # optional argument

    args = parser.parse_args()

    globals()['model'] = args.model
    globals()['question_order'] = args.order

    start_time = time_module.time()
    # total_iterations can be modified. Has to be at least  one more than test cases number as the last solution should also be tested
    total_iterations = 11
    all_question_names, all_question_descriptions, all_test_cases = fetch_question_details(args.questions_file,
                                                                                           args.start if args.start else 0)

    for i in range(0, len(all_question_names)):
        ques_start_time = time_module.time()
        solution_found = False
        iteration_state = constants.GET_MODEL_RESPONSE
        iteration_count = 0
        test_case_failed_number = 0

        # fetch details of a question
        question_name = all_question_names[i]
        question_description = all_question_descriptions[i]
        test_cases = all_test_cases[i]
        message = []

        # csv variables
        globals()['questionName'] = [question_name]
        globals()['questionDescription'] = [question_description]

        while iteration_count < total_iterations and not solution_found:
            iteration_start_time = time_module.time()
            feedback = None
            if iteration_state == constants.GET_MODEL_RESPONSE:
                printToTerminalFile("\nAsking ChatGPT for a response Python solution for : ", question_name)
                # Generate a solution via ChatGPT and save it
                initial_message = ("You are an expert Python code developer. Understand what the question asks and "
                                   "write an executable Python code for the given problem. Write the code in one "
                                   "function only. You need to only provide the code output and no explanation, "
                                   "comments, markdown, code fence, etc are needed. Declare function variables as "
                                   "stated in the question and in the same order. Do not enclose the response in "
                                   "```python. Do not use variable names like time, os or other python module names. ")
                message.append({"role": "system", "content": initial_message})
                message.append({"role": "user", "content": question_description})

                # csv variable
                globals()['promptList'][0].append(initial_message + " " + question_description)

                response = chat_with_chatgpt(message, model)
                printToTerminalFile("ChatGPT response python solution:\n", response)
                message.append({"role": "assistant", "content": response})

                printToTerminalFile("Saving the solution")
                saved, error = save_code(response, question_name, iteration_count)
                if saved:
                    iteration_state = constants.COMPILE_CODE
                    iteration_count += 1
                    printToTerminalFile("Iteration state changed: ", iteration_state)
                else:
                    feedback = "Could not save code. Can you modify the code as per the following error: " + error
                    printToTerminalFile(feedback)
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    # csv variable
                    globals()['errorList'][0].append(feedback)

            if iteration_state == constants.COMPILE_CODE:
                printToTerminalFile('Compiling the solution')
                # Check for code compilation and other errors. First install uninstalled libraries.
                imports_install_message = install_imports(response, model)
                printToTerminalFile(imports_install_message)
                if imports_install_message == "Installed new imports successfully!":
                    code_output, feedback = compile_code(response)
                    printToTerminalFile(code_output)
                    if code_output == "Failed to compile!":
                        iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                        feedback = feedback + "The previous solution failed to compile. Can you please generate a solution that executes."
                        globals()['errorList'][0].append(code_output)

                    else:
                        iteration_state = constants.TEST_CODE
                        printToTerminalFile("Iteration state changed: ", iteration_state)
                else:
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    feedback = "The previous solution gives the following error: " + imports_install_message
                    globals()['errorList'][0].append(feedback)

            if iteration_state == constants.TEST_CODE:
                printToTerminalFile('Testing the solution')
                printToTerminalFile(test_cases)
                all_test_cases_pass, test_case_failed, test_case_feedback = test_code(response, test_cases,
                                                                                      question_description)
                # csv variable
                globals()['testsFailedList'][0].append(test_case_failed)
                globals()['errorList'][0].append(test_case_feedback)

                if all_test_cases_pass:
                    solution_found = True
                else:
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    feedback = test_case_feedback
                    test_case_failed_number = test_case_failed

            if iteration_state == constants.UPDATE_QUESTION_DESCRIPTION:
                printToTerminalFile("Updating the prompt to include : ", feedback)
                message.append({"role": "user", "content": feedback})

                # csv variable
                globals()['promptList'][0].append(feedback)

                response = chat_with_chatgpt(message, model)

                printToTerminalFile("Updated ChatGPT response. Python solution:\n", response)
                message.append({"role": "assistant", "content": response})

                printToTerminalFile("Saving the updated solution")
                saved, error = save_code(response, question_name, iteration_count)
                if saved:
                    iteration_state = constants.COMPILE_CODE
                    iteration_state = constants.COMPILE_CODE
                    iteration_count += 1
                    printToTerminalFile("Iteration state changed: ", iteration_state)
                else:
                    feedback = "Could not save code. Can you modify the code as per the following error: " + error
                    printToTerminalFile(feedback)
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    # csv variable
                    globals()['errorList'][0].append(feedback)
            # csv variable
            globals()['timeReq'][0].append(time_module.time() - iteration_start_time)

        if iteration_count <= total_iterations:
            if solution_found:
                # csv variable
                globals()['solved'] = ['Yes']
                globals()['iterationSolved'] = [iteration_count]
                printToTerminalFile("ChatGPT found a solution for problem " + question_name + " in " + str(
                    iteration_count) + " iterations!")
            else:
                # csv variable
                globals()['solved'] = ['No']
                globals()['iterationSolved'] = [iteration_count]
                printToTerminalFile("ChatGPT could not find a solution for problem " + question_name + " !")

        # csv variable
        globals()['totalTimeReq'].append(time_module.time() - ques_start_time)
        resultCSV()

        printToTerminalFile("Total time required : ", str(time_module.time() - start_time))
