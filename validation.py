import argparse
import ast
import csv
import re
import sys
import os as os_module
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import requests
import time
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import json
import astor

class LeetCodeBot:

    def __init__(self, username, password, model):
        self.session = requests.Session()
        self.model = model
        self.username = username
        self.password = password
        self.csrf_token = None
        self.cookies = None
    def login_with_selenium(self):

        options = webdriver.ChromeOptions()
        #options.add_argument("--headless")
        #options.add_argument("--disable-gpu")
        #options.add_argument("--incognito")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://leetcode.com/accounts/login/")

        try:
            # wait = WebDriverWait(driver, 20)
            # wait.until(EC.visibility_of_element_located((By.ID, 'id_login')))
            # username_input = driver.find_element(By.ID,'id_login')
            # wait.until(EC.visibility_of_element_located((By.ID, 'id_password')))
            # password_input = driver.find_element(By.ID, 'id_password')
            # username_input.send_keys(self.username)
            # password_input.send_keys(self.password)
            # time.sleep(3)
            # password_input.send_keys(Keys.ENTER)
            input("Please complete the CAPTCHA manually and press Enter when done...")

            time.sleep(5)
            self.printToTerminalFile(driver.get_cookies())
            self.cookies = driver.get_cookies()
            for cookie in self.cookies:
                if cookie['name'] == 'csrftoken':
                    self.csrf_token = cookie['value']
                    break
            for cookie in self.cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            if 'LEETCODE_SESSION' in [cookie['name'] for cookie in self.cookies]:
                self.printToTerminalFile("Login successful!")
                return True
            else:
                self.printToTerminalFile("Login failed. Please check your credentials.")
                return False
        except Exception as e:
            self.printToTerminalFile("An error occurred during login:", e)
            driver.quit()

    def get_testcases_codeDef(self, question_slug):
        print("question slug is :", question_slug)
        url = "https://leetcode.com/graphql/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
            "Content-Type": "application/json",
            "x-csrftoken": self.csrf_token,
        }
        query_payload = {
            "operationName": "questionData",
            "variables": {
                "titleSlug": question_slug
            },
            "query": """
                query questionData($titleSlug: String!) {
                    question(titleSlug: $titleSlug) {
                        questionId
                        title
                        content
                        difficulty
                        stats
                        codeDefinition
                        sampleTestCase
                        exampleTestcases
                        metaData
                    }
                }
            """
        }
        response = self.session.post(url, headers=headers, data=json.dumps(query_payload))
        if response.status_code == 200:
            data = response.json()
            question_data = data.get('data', {}).get('question', {})
            if question_data:
                print(question_data)
                example_test_cases = question_data.get('exampleTestcases')
                question_id = question_data.get('questionId')
                if 'python3' in question_data.get('metaData') or ('python3' in question_data.get('codeDefinition')):
                    def_code = eval(question_data.get('codeDefinition'))[3]['defaultCode']
                else:
                    def_code = None
                return example_test_cases, def_code, question_id
            else:
                self.printToTerminalFile("Question not found or data is empty.")
                return None, None, None
        else:
            self.printToTerminalFile(f"Failed to fetch question data. Status code: {response.status_code}")
            return None, None, None

    def find_function_body(self, code):
        def get_function_body(func_node):
            body_nodes = func_node.body
            body_lines = [ast.get_source_segment(code, node) for node in body_nodes]
            return ''.join(body_lines)

        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name != "main":
                #self.printToTerminalFile(get_function_body(node))
                return get_function_body(node)
        return None


    def exchange_func_body(self, first_code, second_code):
        def extract_non_main_function_body(tree):
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name != "main":
                    return node.body
            return None

        def insert_function_body(tree, function_body):
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    node.body.clear()
                    node.body.extend(function_body)
                    break
        try:
            first_tree = ast.parse(first_code+'pass')
            second_tree = ast.parse(second_code)
            non_main_function_body = extract_non_main_function_body(second_tree)
            if non_main_function_body:
                insert_function_body(first_tree, non_main_function_body)
            modified_code = astor.to_source(first_tree)
        except Exception as e:
            modified_code = second_code
        return modified_code

    def interpret_solution(self, question_url, question_name, solution_code):
        self.printToTerminalFile(question_url, question_name)
        data_input, code_def, question_id = self.get_testcases_codeDef(question_url.split('/')[-1])
        if data_input:
            modified_code = self.exchange_func_body(code_def, solution_code) if code_def else solution_code
            self.printToTerminalFile(modified_code)
            lang = 'python3'
            self.session.get(question_url)
            #question_id = question_name.split(".")[0]
            self.printToTerminalFile("Inside interpret solution with question id: ", question_id)
            if not question_id:
                self.printToTerminalFile("Could not retrieve question ID.")
                return

            interpret_url = question_url + '/interpret_solution/'
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
                'x-csrftoken': self.csrf_token,
                'referer': question_url,
                'Content-Type': 'application/json',
                }
            payload = {
                'lang': lang,
                'question_id': question_id,
                'typed_code': modified_code,
                'data_input': data_input
            }
            response = self.session.post(interpret_url, headers=headers, data=json.dumps(payload))
            time.sleep(5)
            if response.status_code == 200:
                interpret_response = response.json()
                self.printToTerminalFile(f"Interpret ID: {interpret_response['interpret_id']}")
                self.printToTerminalFile(payload)
                #self.printToTerminalFile(f"Test Cases: {interpret_response['test_case']}")
                return interpret_response
            else:
                self.printToTerminalFile("Error interpreting solution:", response.text)
                self.printToTerminalFile(response.status_code)
                self.printToTerminalFile(response.content)
                return None
        else:
            self.printToTerminalFile("Unable to find test cases!")
            return None
    def check_status(self, interpret_id, stage, max_retries=10, wait_time=5):
        print(interpret_id)
        self.printToTerminalFile("Inside Check solution")
        check_url = f'https://leetcode.com/submissions/detail/{interpret_id}/check/'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
            'x-csrftoken': self.csrf_token,
            'referer': f'https://leetcode.com/submissions/detail/{interpret_id}/',
            'Content-Type': 'application/json',
        }

        for attempt in range(max_retries):
            response = self.session.get(check_url, headers=headers)
            result = response.json()
            if response.status_code == 200:
                self.printToTerminalFile(f"Attempt {attempt + 1}: {result}")
                state = result.get('state', None)
                if state == 'PENDING':
                    self.printToTerminalFile("Solution is still pending. Retrying...")
                    time.sleep(wait_time)
                elif state == 'SUCCESS':
                    run_success = result.get('run_success', None)
                    total_correct = result.get('total_correct', 0)
                    total_testcases = result.get('total_testcases', 0)
                    if run_success and total_correct == total_testcases:
                        self.printToTerminalFile(result)
                        self.printToTerminalFile(f"Solution passed all test cases! ({total_correct}/{total_testcases})")
                        result['stage'] = stage
                        result['error'] = None
                        return True, result
                    else:
                        result['stage'] = stage
                        result['error'] = "Failed to pass all Test Cases"
                        self.printToTerminalFile(result)
                        self.printToTerminalFile(f"Solution failed. Passed {total_correct}/{total_testcases} test cases.")
                        return False, result
                else:
                    result['stage'] = stage
                    result['error'] = f"Unexpected state: {state}"
                    self.printToTerminalFile(f"Unexpected state: {state}")
                    return False, result
            else:
                result['stage'] = stage
                result['error'] = f"Error fetching status: {response.status_code}"
                self.printToTerminalFile(f"Error fetching status: {response.status_code}")
                return False, result
        self.printToTerminalFile("Max retries exceeded. Solution did not complete in time.")
        return False, None

    def submit_solution(self, question_url, question_name, solution_code):
        data_input, code_def, question_id = self.get_testcases_codeDef(question_url.split('/')[-1])
        modified_code = self.exchange_func_body(code_def, solution_code) if code_def else solution_code
        print("----------------------------------------------")
        print(modified_code)
        #question_id = question_name.split(".")[0]
        submit_url = f'{question_url}/submit/'
        lang = 'python3'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36",
            'x-csrftoken': self.csrf_token,
            'referer': question_url,
            'Content-Type': 'application/json',
        }
        payload = {
            'lang': lang,
            'question_id': question_id,
            'typed_code': modified_code
        }
        response = self.session.post(submit_url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            submit_response = response.json()
            submission_id = submit_response.get('submission_id')
            if submission_id:
                self.printToTerminalFile(f"Submission successful! Submission ID: {submission_id}")
                return submission_id
            else:
                self.printToTerminalFile("Submission failed. No submission ID found in response.")
                return None
        else:
            self.printToTerminalFile(f"Error submitting solution: {response.status_code}")
            return None

    def store_result_in_csv(self, question_name, result):
        # log question_name submission_id run_success total_correct total_testcases status_memory memory_percentile status_runtime runtime_percentile
        fields = ['Question Name', 'Stage', 'Error', 'Submission Id', 'Run Success', 'Total Correct', 'Total Testcases', 'Status Memory', 'Memory Percentile',
                  'Status Runtime', 'Runtime Percentile', 'code Output', 'Std Output', 'Last Testcase', 'Expected Output', 'Status Msg']
        filename = 'leetCode_submission_results_'+self.model+'.csv'
        with open(filename, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow({
                'Question Name': question_name,
                'Stage': result.get('stage', None),
                'Error': result.get('error', None),
                'Submission Id': result.get('submission_id', None),
                'Run Success': result.get('run_success', None),
                'Total Correct': result.get('total_correct', None),
                'Total Testcases': result.get('total_testcases', None),
                'Status Memory': result.get('status_memory', None),
                'Memory Percentile': result.get('memory_percentile', None),
                'Status Runtime': result.get('status_runtime', None),
                'Runtime Percentile': result.get('runtime_percentile', None),
                'code Output': result.get('code_output', None),
                'Std Output': result.get('std_output', None),
                'Last Testcase': result.get('last_testcase', None),
                'Expected Output': result.get('expected_output', None),
                'Status Msg': result.get('status_msg', None)
            })

        self.printToTerminalFile(f"Results stored in {filename}")

    def printToTerminalFile(self, *args, **kwargs):
        original_stdout = sys.stdout
        print(*args, **kwargs)
        try:
            file_name = "ChatGPTValidationLogOutput_" + model + ".txt"
            f = open(file_name, 'a', encoding="utf-8")
            sys.stdout = f
            print(*args, **kwargs)
            sys.stdout = original_stdout
            f.close()
        finally:
            sys.stdout = original_stdout

    def find_largest_numbered_file(self, folder_path):
        largest_number = 0
        largest_file = None
        for file_name in os_module.listdir(folder_path):
            match = re.search(r'_(\d+)\.py$', file_name)
            if match:
                number = int(match.group(1))
                if number > largest_number:
                    largest_number = number
                    largest_file = file_name
                else:
                    largest_file = file_name

        return largest_file

    def fetch_solved_solution(self, excel_file_name, data_file, base_path_sol):
        question_names = []
        question_urls = []
        saved_solutions = []
        if os_module.path.exists(excel_file_name) and os_module.path.exists(data_file):
            self.printToTerminalFile("Fetching question details...")
            rf = pd.read_excel(excel_file_name)       #as many to check!
            df = pd.read_excel(data_file)
            df_merged = pd.merge(rf, df, on='Question Name')
            all_rows = df_merged.values.tolist()
            for question in range(0, len(all_rows)):
                #print(all_rows[question])
                if all_rows[question][8] == 'Yes':
                    question_names.append(all_rows[question][1])
                    question_urls.append(all_rows[question][12])
                    folder_name = all_rows[question][1].replace(" ", "").replace(":", "_").replace("?", "").replace("/", "_")
                    folder_path = os_module.path.join(base_path_sol, folder_name)
                    if os_module.path.exists(folder_path) and os_module.path.isdir(folder_path):
                        largest_file_name = self.find_largest_numbered_file(folder_path)
                        if largest_file_name:
                            largest_file_path = os_module.path.join(folder_path, largest_file_name)
                            with open(largest_file_path, 'r') as solution:
                                solution_content = solution.read()
                                saved_solutions.append(solution_content)
                                #self.printToTerminalFile(solution_content)
                        else:
                            saved_solutions.append(None)
                            self.printToTerminalFile("No file with a numbered suffix found.")
                    else:
                        saved_solutions.append(None)
                        self.printToTerminalFile("Folder does not exist.", all_rows[question][1])
        else:
            self.printToTerminalFile("Could not find question details file path!")
        self.printToTerminalFile("Finished fetched ", len(question_names), " questions.\n")
        return question_names, question_urls, saved_solutions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model selection.")
    parser.add_argument("model", help="Model selection type.")
    parser.add_argument("-rf", "--response_file", help="Response file to validate")
    parser.add_argument("-df", "--data_file", help="LeetCode dataset file")
    parser.add_argument("-sp", "--sol_path", help="Base path for the Solutions folder")
    parser.add_argument("-s", "--start", type=int, help="Question number to start with")
    parser.add_argument("-u", "--user", help="LeetCode account username")
    parser.add_argument("-p", "--password", help="LeetCode account password")
    args = parser.parse_args()
    model = args.model
    username = args.user
    password = args.password

    bot = LeetCodeBot(username, password, model)
    logged_in = bot.login_with_selenium()
    question_names, question_urls, saved_solutions =bot.fetch_solved_solution(args.response_file, args.data_file, args.sol_path)
    print(len(question_names))
    for i, question_name in enumerate(question_names):
        if saved_solutions[i]:
            if logged_in:
                interpret_response = bot.interpret_solution(question_urls[i], question_names[i], saved_solutions[i])
                if interpret_response:
                    interpret_id = interpret_response.get('interpret_id', None)
                    to_submit, response = bot.check_status(interpret_id, "Initial Interpret")
                    if to_submit:
                        submission_id = bot.submit_solution(question_urls[i], question_names[i], saved_solutions[i])
                        if submission_id:
                            completed, response = bot.check_status(submission_id, "Submitting")
                            bot.store_result_in_csv(question_name, response)
                    else:
                        bot.store_result_in_csv(question_name, response)
                        bot.printToTerminalFile("Failed to check solution.")
                else:
                    bot.printToTerminalFile("Failed to interpret solution.")
            else:
                bot.printToTerminalFile("Failed to login! Please try again")
        else:
            bot.printToTerminalFile("Failed to fetch solution! Please try again")
        time.sleep(10)
