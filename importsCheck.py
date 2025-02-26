import subprocess
import ast
import sys

model = "o1-mini"


def printToTerminalFile(*args, **kwargs):
    """ Logs messages both to the terminal and a log file. """
    file_name = f"ResponseLog_{model}.txt"
    print(*args, **kwargs)

    with open(file_name, 'a', encoding="utf-8") as f:
        print(*args, **kwargs, file=f)


def extract_modules_to_import(code):
    """ Extracts the modules that needs to be imported to run the given code. """
    try:
        ast_tree = ast.parse(code)
    except SyntaxError as e:
        printToTerminalFile(f"Syntax error while parsing code: {e}")
        return []
    modules_to_import = set()
    for node in ast.walk(ast_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:  # Iterate through the aliases
                modules_to_import.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules_to_import.add(node.module)
    return list(modules_to_import)


def is_standard_library(module_name):
    """ Checks if a module is part of Python's standard library. """
    return module_name in sys.builtin_module_names or module_name in sys.stdlib_module_names


def install_imports(code, model_new):
    """ Installs any missing modules specified in the code. """
    if not code:
        return "No code provided. Please provide Python code with necessary imports.", False
    global model
    model = model_new

    modules_to_import = extract_modules_to_import(code)
    if not modules_to_import:
        return "No modules to import.", True
    # Exclude standard library modules from the list
    third_party_modules = [module for module in modules_to_import if not is_standard_library(module)]
    if not third_party_modules:
        return "All required modules are either standard library or already installed.", True
    try:
        # fetch already installed modules
        installed_modules = set(line.split('==')[0] for line in subprocess.run(['pip', 'freeze'], stdout=subprocess.PIPE, text=True).stdout.splitlines())
        # Install required modules using pip
        modules_to_install = list([module for module in third_party_modules if module not in installed_modules])
        if modules_to_install:
            printToTerminalFile("Installing missing modules:", modules_to_install)
            # to check pip version errors
            subprocess.run(["python", "-m", "pip", "install", "--upgrade", "pip"], check=True)
            subprocess.run(['pip', 'install'] + modules_to_install, check=True)
            return "Installed new imports successfully!", True
        else:
            return "All required modules are already installed.", True
    except Exception as e:
        error_message = f"Module installation failed: {e}"
        printToTerminalFile(error_message)
        return error_message, False
