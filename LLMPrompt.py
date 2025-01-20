import openai
import itertools
import constants
import argparse
import testCaseParser
import pandas as pd
import traceback
import ast
import os as os_module
import time as time_module
from importsCheck import install_imports
from func_timeout import func_timeout, FunctionTimedOut


class SolutionAssistant:
    """Assists in generating, testing, and iterating code solutions using LLMs."""

    def __init__(self, model="gpt-3.5-turbo", question_order=True):
        self.model = model
        self.message = []
        self.question_order = question_order
        self.question_data = {
            'Question Name': [],
            'Question Description': [],
            'Test Cases List': [[]],
            'Prompt List': [[]],
            'Token Length Prompt': [[]],
            'Token Length Response': [[]],
            'Error List': [[]],
            'Tests Failed List': [[]],
            'Solved': [],
            'Iteration Solved': [],
            'Time Req': [[]],
            'Total Time Req': []
        }

    def log_to_file(self, *args, **kwargs):
        """Logs messages to both the terminal and a file."""
        file_name = f"ResponseLog_{self.model}.txt"
        print(*args, **kwargs)
        with open(file_name, 'a', encoding="utf-8") as log_file:
            print(*args, **kwargs, file=log_file)

    def save_results_to_csv(self):
        """Writes the question data to a CSV file."""
        self.log_to_file("Saving results to CSV...")
        csv_file_name = f"ResponseList_{self.model}.csv"
        df = pd.DataFrame(self.question_data)
        if os_module.path.exists(csv_file_name):
            df.to_csv(csv_file_name, header=False, mode='a')
        else:
            df.to_csv(csv_file_name)
        reset_keys = ['Test Cases List', 'Prompt List', 'Token Length Prompt', 'Token Length Response', 'Error List', 'Tests Failed List',
                      'Time Req']
        for key in self.question_data.keys():
            self.question_data[key] = [[]] if key in reset_keys else []

    def get_llm_response(self):
        """Fetches a response from the LLM."""
        try:
            response_code = openai.ChatCompletion.create(
                model=self.model,
                messages=self.message,
                temperature=1,
            )
            self.question_data['Token Length Prompt'][0].append(response_code.usage.prompt_tokens)
            self.question_data['Token Length Response'][0].append(response_code.usage.completion_tokens)

            self.log_to_file("LLM Model used:", response_code.model)
            return response_code.choices[0].message.content.strip()
        except Exception as e:
            self.log_to_file("Error in LLM response:", str(e))
            return None

    def save_code(self, code, filename, version):
        """Saves the generated code to a file."""
        folder_name = filename.replace(" ", "").replace(":", "_").replace("?", "").replace("/", "_")
        path = f"Solutions_{self.model}/{folder_name}"
        os_module.makedirs(path, exist_ok=True)
        file_path = f"{path}/{folder_name}_Solution_{version}.py"
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(code)
            self.log_to_file("Solution saved successfully!")
            return True, None
        except Exception as e:
            self.log_to_file("Error saving solution:", str(e))
            return False, str(e)

    def compile_code(self, code):
        """Compiles the provided Python code."""
        try:
            func_timeout(10, exec, args=(code, globals()))
            self.log_to_file("Code compiled successfully.")
            return "Code compiled successfully!", None
        except FunctionTimedOut:
            feedback = "Code could not be compiled within 10 seconds and was terminated. Possibly due to an infinite loop. Please modify the code accordingly."
            self.log_to_file(feedback)
            return "Failed to compile!", feedback
        except Exception as e:
            self.log_to_file("Failed to compile as an Exception occurred.", str(e))
            return "Failed to compile!", str(e)

    @staticmethod
    def fetch_function_name(code):
        """Extracts the function name from the provided code."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name != "main":
                    return node.name
        except Exception as e:
            return None

    def test_code(self, code, test_cases, question_description, data_source):
        """Tests the provided code against given test cases and returns an appropriate feedback. """

        feedback = ""
        output_list = []
        try:
            function_name = self.fetch_function_name(code)
            if function_name is None:
                feedback = (
                    "Please modify the code. No function found in the solution. You should return a code with a function written in "
                    "Python that solves the problem.")
                return False, 0, feedback

            self.log_to_file("Parsing test cases for function:", function_name)
            test_cases_parsed = testCaseParser.parse_test_case(test_cases) if data_source != 'user' else test_cases
            self.log_to_file("Parsed Test Case:", test_cases_parsed)

            self.question_data['Test Cases List'][0].append(test_cases_parsed)
            for i, test_case in enumerate(test_cases_parsed):
                inputs = test_case['Input']
                expected_output = test_case['Output']
                if isinstance(inputs, list) or isinstance(inputs, tuple):
                    returned_output = func_timeout(30, globals()[function_name], args=(*inputs,))
                else:
                    returned_output = func_timeout(30, globals()[function_name], args=(inputs,))
                self.log_to_file(
                    f"Input: {inputs}\n Output Returned: {returned_output}\n Output Expected: {expected_output}")

                # Compare the output with the expected output as output stored/fetched from dataset is string not bool
                if isinstance(returned_output, bool) and (expected_output == 'true' or expected_output == 'True'):
                    expected_output = True
                elif isinstance(returned_output, bool) and (expected_output == 'false' or expected_output == 'False'):
                    expected_output = False
                # Adding test cases to the question message
                if returned_output != expected_output:
                    any_order = ["return the answer in any order", "return the solution in any order",
                                 "return the values in any order"]
                    if self.question_order and any(order in question_description for order in any_order) and isinstance(
                            returned_output, list):
                        # Can handle only simple permutations on the entire output not partially allowed permutations
                        permutated_returned_output = func_timeout(60, list(itertools.permutations),
                                                                  args=(returned_output,))
                        if expected_output in permutated_returned_output:
                            self.log_to_file("Test case passed!\n")
                            output_list.append(returned_output)
                            break
                        else:
                            self.log_to_file("Output returned is not as expected! \n")
                            feedback += (
                                f" Please modify the code. The previous solution gives incorrect results. "
                                f"Failed test case: Input: {inputs} \n Expected Output: {expected_output}. "
                                f"Use different concepts or change small segments of the generated code to "
                                f"make it satisfy the test case. Expected output: {expected_output} but output "
                                f"returned is: {returned_output}")
                            # self.log_to_file(feedback)
                            return False, i + 1, feedback
                    else:
                        self.log_to_file("Output returned is not as expected! \n")
                        feedback += (
                            f" Please modify the code. The previous solution gives incorrect results. "
                            f"Failed test case: Input: {inputs} \n Expected Output: {expected_output}. "
                            f"Use different concepts or change small segments of the generated code to "
                            f"make it satisfy the test case. Expected output: {expected_output} but output "
                            f"returned is: {returned_output}")
                        # self.log_to_file(feedback)
                        return False, i + 1, feedback
                else:
                    self.log_to_file("Test case passed!\n")
                    output_list.append(returned_output)
            if len(output_list) == len(test_cases_parsed):
                return True, 0, None
        except FunctionTimedOut as fte:
            feedback = "Code could not be compiled within 30 seconds and was terminated. Possibly due to an infinite loop or order of the results. Please modify the code accordingly."
            self.log_to_file(feedback, str(fte))
            return False, i + 1, feedback
        except Exception as e:
            traceback.print_exc()
            feedback += f"Please modify the code. The previous solution gives the following error: \n {str(e)}"
            return False, i + 1, feedback
        return False, 0, feedback


def fetch_question_details(excel_file_name, order, start=1):
    """ This function reads the LeetCode file and fetches the data. """
    excel_file_path = excel_file_name
    question_names = []
    question_descriptions = []
    test_cases = []
    if os_module.path.exists(excel_file_path):
        print("Fetching question details...")
        df = pd.read_excel(excel_file_path)
        all_rows = df.values.tolist()

        for question in range(start, len(all_rows)):
            # ensure question_names, question_descriptions, test_cases are not null
            # ensure it is not a premium question and that there is at least 1 test case available
            # #ensure the answer is not asking for results in any order
            if (all_rows[question][0] and all_rows[question][5] and all_rows[question][7]
                    and ('in any order' not in str(all_rows[question][5]) if order is False else True)
                    and all_rows[question][2] != "Yes" and all_rows[question][6] > 0):
                question_names.append(all_rows[question][0])
                question_descriptions.append(all_rows[question][5])
                test_cases.append(all_rows[question][7])
    else:
        print("Could not find the given file path!")
    print("Fetched ", len(question_names), " questions.\n")
    return question_names, question_descriptions, test_cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model selection.")
    parser.add_argument("model", help="The OpenAI model to query")
    parser.add_argument("-k", "--openai_key", help="OpenAI Key")
    parser.add_argument("-d", "--data_by", help="Data is given by user or leetcode")
    parser.add_argument("-o", "--order", action="store_true", help="Test questions which return solutions in any order")

    args = parser.parse_args()
    if (args.data_by).lower() == 'user':
        #Ask for question description and test cases
        all_question_names = ["User Question"]
        all_question_descriptions = [input("Please enter the question description: ")]
        all_test_cases = []
        while True:
            test_input = input("Enter the test case Input: ")
            test_output = input("Enter the test case Output: ")
            all_test_cases.append({'Input': testCaseParser.safe_literal_eval(test_input)[1],
                                   'Output': testCaseParser.safe_literal_eval(test_output)[1]})
            more_tests = input("Do you want to add another test case? (yes/no): ").strip().lower()
            if more_tests not in ['yes', 'y']:
                break
    else:
        #Ask for the path of the question file and start
        questions_file = input("Please enter the path of the data file: ")
        start = input("Please enter the starting question number: ")
        all_question_names, all_question_descriptions, all_test_cases = fetch_question_details(questions_file,
                                                                                               args.order, int(start))

    #Initialize the API key
    openai.api_key = args.openai_key if args.openai_key else os_module.getenv("OPENAI_API_KEY")
    start_time = time_module.time()
    # total_iterations can be modified. Should be at least one more than test cases number
    total_iterations = 11

    for i in range(0, len(all_question_names)):
        assistant = SolutionAssistant(args.model, args.order)

        ques_start_time = time_module.time()
        solution_found = False
        iteration_state = constants.GET_MODEL_RESPONSE
        iteration_count = 0
        test_case_failed_number = 0

        # fetch details of a question
        question_name = all_question_names[i]
        question_description = all_question_descriptions[i]
        test_cases = all_test_cases[i] if (args.data_by).lower() != 'user' else all_test_cases
        assistant.question_data['Question Name'].append(question_name)
        assistant.question_data['Question Description'].append(question_description)

        while iteration_count <= total_iterations and not solution_found:
            iteration_start_time = time_module.time()
            feedback = None
            if iteration_state == constants.GET_MODEL_RESPONSE:
                assistant.log_to_file("\nAsking the model for a response Python solution for : ", question_name)
                # Generate a solution and save it
                initial_message = ("You are an expert Python code developer. Understand what the question asks and "
                                   "write an executable Python code for the given problem. Write the code in one "
                                   "function only. You need to only provide the code output and no explanation, "
                                   "comments, markdown, code fence, etc are needed. Declare function variables as "
                                   "stated in the question and in the same order. Do not enclose the response in "
                                   "```python. Do not use variable names like time, os or other existing python module names. ")
                if assistant.model == "o1-mini":
                    assistant.message.append(
                        {"role": "user", "content": initial_message})  # as there is no system message for this model
                else:
                    assistant.message.append({"role": "system", "content": initial_message})

                assistant.message.append({"role": "user", "content": question_description})
                assistant.question_data['Prompt List'][0].append(initial_message + " " + question_description)

                response = assistant.get_llm_response()
                assistant.log_to_file("LLM response python solution:\n", response)
                assistant.message.append({"role": "assistant", "content": response})

                assistant.log_to_file("Saving the solution")
                saved, error = assistant.save_code(response, question_name, iteration_count)
                if saved:
                    iteration_state = constants.COMPILE_CODE
                    iteration_count += 1
                    assistant.log_to_file("Iteration state changed: ", iteration_state)
                else:
                    feedback = "Could not save code. Can you modify the code as per the following error: " + error
                    assistant.log_to_file(feedback)
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    assistant.question_data['Error List'][0].append(feedback)

            if iteration_state == constants.COMPILE_CODE:
                assistant.log_to_file('\nCompiling the solution')
                # Check for code compilation and other errors. First install uninstalled libraries.
                imports_install_message, installed = install_imports(response, args.model)
                assistant.log_to_file(imports_install_message)
                if installed:
                    code_output, feedback = assistant.compile_code(response)
                    if code_output == "Failed to compile!":
                        iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                        feedback = feedback + "The previous solution failed to compile. Can you please generate a solution that executes."
                        assistant.question_data['Error List'][0].append(code_output)

                    else:
                        iteration_state = constants.TEST_CODE
                        assistant.log_to_file("Iteration state changed: ", iteration_state)
                else:
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    feedback = "The previous solution gives the following error: " + imports_install_message
                    assistant.question_data['Error List'][0].append(feedback)

            if iteration_state == constants.TEST_CODE:
                assistant.log_to_file('\nTesting the solution')
                all_test_cases_pass, test_case_failed, test_case_feedback = assistant.test_code(response, test_cases,
                                                                                                question_description,
                                                                                                (args.data_by).lower())
                # csv variable
                assistant.question_data['Tests Failed List'][0].append(test_case_failed)
                assistant.question_data['Error List'][0].append(test_case_feedback)

                if all_test_cases_pass:
                    solution_found = True
                elif iteration_count == total_iterations:  # no solution found by llm
                    feedback = test_case_feedback
                    test_case_failed_number = test_case_failed
                    break
                else:  # Failed to pass a test case. Move to next iteration.
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    feedback = test_case_feedback
                    test_case_failed_number = test_case_failed

            if iteration_state == constants.UPDATE_QUESTION_DESCRIPTION and iteration_count < total_iterations:
                assistant.message.append({"role": "user", "content": feedback})

                assistant.question_data['Prompt List'][0].append(feedback)
                assistant.log_to_file("Updated the prompt to include : ", feedback)

                response = assistant.get_llm_response()

                assistant.log_to_file("Updated LLM response. Python solution:\n", response)
                assistant.message.append({"role": "assistant", "content": response})

                assistant.log_to_file("Saving the updated solution")
                saved, error = assistant.save_code(response, question_name, iteration_count)
                if saved:
                    iteration_state = constants.COMPILE_CODE
                    iteration_count += 1
                    assistant.log_to_file("Iteration state changed: ", iteration_state)
                else:
                    feedback = "Could not save code. Can you modify the code as per the following error: " + error
                    assistant.log_to_file(feedback)
                    iteration_state = constants.UPDATE_QUESTION_DESCRIPTION
                    assistant.question_data['Error List'][0].append(feedback)
            if iteration_state == constants.UPDATE_QUESTION_DESCRIPTION and iteration_count >= total_iterations:
                break
            if iteration_start_time:
                assistant.question_data['Time Req'][0].append(time_module.time() - iteration_start_time)

        if iteration_count <= total_iterations:
            if solution_found:
                assistant.question_data['Solved'] = ['Yes']
                assistant.question_data['Iteration Solved'] = [iteration_count]
                assistant.log_to_file("LLM found a solution for problem " + question_name + " in " + str(
                    iteration_count) + " iterations!")
            else:
                assistant.question_data['Solved'] = ['No']
                assistant.question_data['Iteration Solved'] = [iteration_count]
                assistant.log_to_file("LLM could not find a solution for problem " + question_name + " !")

        assistant.question_data['Total Time Req'].append(time_module.time() - ques_start_time)
        assistant.save_results_to_csv()

        assistant.log_to_file("Total time required : ", str(time_module.time() - start_time))
