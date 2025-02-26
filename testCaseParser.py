import re
import ast

def safe_literal_eval(node):
    """  evaluates valid Python datatypes dynamically. """
    if not isinstance(node, str):
        return True, node

    node = node.replace('null', 'None')
    try:
        return True, ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return False, node

def replace_boolean_strings(input):
    """ Replaces string representations of booleans from test cases"""
    if isinstance(input, str) and ("true" in input.lower() or "false" in input.lower()):
        value = re.sub(r'\btrue\b', 'True', input, flags=re.IGNORECASE)
        value = re.sub(r'\bfalse\b', 'False', value, flags=re.IGNORECASE)
        value = value.replace('null','None')
        return eval(value)

    if isinstance(input, (list, tuple, set)):
        return type(input)(replace_boolean_strings(v) for v in input)
    elif isinstance(input, dict):
        return {k: replace_boolean_strings(v) for k, v in input.items()}

    return input


def parse_test_case(test_cases: str):
    """Parses test cases from a string to valid Python data types."""
    test_cases = [tc.strip() for tc in ast.literal_eval(test_cases)]
    parsed_test_cases = []

    input_pattern = re.compile(r'Input: (.+?)\nOutput', re.DOTALL)
    output_pattern = re.compile(r'Output: (.+?)(?:\nExplanation|\Z)', re.DOTALL)

    for test_case in test_cases:
        input_match = input_pattern.search(test_case)
        output_match = output_pattern.search(test_case)

        if input_match and output_match:
            raw_input, raw_output = input_match.group(1), output_match.group(1).replace('\n', '')
            # Extracting input values
            if ' = ' in raw_input:
                raw_input = raw_input.split(' = ')[1:]

            if isinstance(raw_input, list) and len(raw_input) > 1:
                parsed_inputs = [safe_literal_eval(inp.rsplit(',', 1)[0])[1] for inp in raw_input[:-1]]
                parsed_inputs.append(safe_literal_eval(raw_input[-1])[1])
            else:
                parsed_inputs = safe_literal_eval(replace_boolean_strings(raw_input))[1]

            # cleaning and evaluating output
            if ' = ' in raw_output:
                raw_output = re.sub(r'\b\w+\s*=\s*([^;]+)', r'\1', raw_output)

            parsed_output = safe_literal_eval(replace_boolean_strings(raw_output))[1]

            parsed_test_cases.append({
                'Input': parsed_inputs,
                'Output': parsed_output
            })

    return parsed_test_cases
