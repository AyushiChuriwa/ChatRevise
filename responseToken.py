import argparse
import tiktoken
import os
import openpyxl

def compute_token(model, code):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(code))
    return num_tokens

def process_directory(base_dir, model):
    results = []
    for folder_name in os.listdir(base_dir):
        folder_path = os.path.join(base_dir, folder_name)
        i=0
        if os.path.isdir(folder_path):
            total_token_count = 0
            for root, _, files in os.walk(folder_path):
                for file_name in files:
                    if file_name.endswith('.py'):
                        file_path = os.path.join(root, file_name)
                        with open(file_path, encoding="utf8") as solution:
                            solution_content = solution.read()
                            token_count = compute_token(model, solution_content)
                            total_token_count += token_count
                results.append((folder_name, total_token_count))
                print(folder_name, total_token_count, i)
            i+=1
    write_to_excel(results, "folder_token_counts"+model+".xlsx")


def write_to_excel(data, file_name):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Token Counts"
    ws.append(["Folder Name", "Total Token Count"])
    for folder_name, token_count in data:
        ws.append([folder_name, token_count])
    wb.save(file_name)
    print(f"Results written to {file_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Token calculation.")
    parser.add_argument("model", help="Model selection type.")
    parser.add_argument("-bd", "--base_dir", help="Base dir for sol")

    args = parser.parse_args()
    base_directory = args.base_dir
    model = args.model
    print("Using tokenizer:", tiktoken.encoding_for_model(model))
    process_directory(base_directory,model)

