import re
import ast

def safe_literal_eval(node):
    """
    This function helps us evaluate valid Python datatypes dynamically.

    :param node: node to evaluate
    :return: Boolean stating the state
    :return: evaluated node
    """
    try:
        evaluated = ast.literal_eval(node)
        return True, evaluated
    except:
        return False, node

def parse_test_case(test_cases):
    """
    This function parses the test cases from string to a valid Python datatype.

    :param test_cases: test cases to parse
    :return: Parsed test cases
    """
    test_cases = ast.literal_eval(test_cases)
    test_cases = [n.strip() for n in test_cases]
    parsed_test_cases = []

    for test_case in test_cases:
        # First search for I/O test cases from the text
        input_match = re.search(r'Input: (.+?)\nOutput', test_case)
        output_match = re.search(r'Output: (.+?)\nExplanation', test_case) if re.search(r'Output: (.+?)\nExplanation',
                                                                                        test_case) else re.search(
            r'Output: (.*)', test_case)

        if input_match and output_match:
            input = input_match.group(1)
            output = output_match.group(1)
            if output and input:
                # Many inputs are just values no variable names.
                if ' = ' in input:
                    input = input.split(' = ')[1:]

                if ' = ' in output:
                    output = re.sub(r'\b\w+\s*=\s*([^;]+)', r'\1', output)

                if len(input) > 1:
                    inputs = []
                    for i in range(len(input) - 1):
                        processed = input[i].rsplit(',', 1)[0]
                        inputs.append(safe_literal_eval(processed.replace('null', 'None'))[1])
                    inputs.append(safe_literal_eval(input[-1].replace('null', 'None'))[1])

                    # Creating dictionary and appending to result list
                    output = output.replace('\n', '')
                    if isinstance(output, str) and 'true' not in output.lower() and 'false' not in output.lower():
                        parse_test_case = {'Input': inputs,
                                           'Output': safe_literal_eval(output.replace('null', 'None'))[
                                               1]}
                    else:
                        parse_test_case = {'Input': inputs, 'Output': output}
                else:
                    if isinstance(output, str) and 'true' not in output.lower() and 'false' not in output.lower():
                        parse_test_case = {
                            'Input': safe_literal_eval(input[0].replace('null', 'None'))[1],
                            'Output': safe_literal_eval(output.replace('null', 'None'))[
                                1]} if isinstance(input, list) else {
                            'Input': safe_literal_eval(input.replace('null', 'None'))[1],
                            'Output': safe_literal_eval(output.replace('null', 'None'))[1]}
                    else:
                        parse_test_case = {
                            'Input': safe_literal_eval(input[0].replace('null', 'None'))[1],
                            'Output': output} if isinstance(input, list) else {
                            'Input': safe_literal_eval(input.replace('null', 'None'))[1],
                            'Output': output}
                    if isinstance(parse_test_case['Input'], list):
                        inp = parse_test_case['Input']
                        parse_test_case['Input'] = [inp]
                parsed_test_cases.append(parse_test_case)
    #print(parsed_test_cases)
    return parsed_test_cases

