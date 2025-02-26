# ChatRevise - Test-Guided Refinement of LLM-Produced Code

## Description
A framework for automated code generation, testing, and repair using Large Language Models (LLMs).

It supports **LeetCode** and **MBPP** datasets and work with models, including:
- OpenAI models: `gpt-3.5-turbo`, `gpt-4o-mini`, `gpt-4o`, `gpt-o1-mini`, `gpt-o3-mini`
- **Gemini** models

## Getting Started
### Prerequisites
Ensure you have the following installed before proceeding:
- **Python**
- **OpenAI API Key** or **Gemini API Key**
- Required dependencies (install using `pip install -r requirements.txt`)

### Setup Instructions
1. Download and unpack the **Solutions.zip** file into the root directory **before running any experiments**.
   **Download link:** [MEGA](https://mega.nz/file/goAh3ZDA#AZvSXAC0CFHG2wmDQ5eTiiTQc7Y3ZyWSqyEpwdKCTjg)

2. Set up a virtual environment and install dependencies:
```bash
python -m venv myenv
myenv\Scripts\activate  # On Windows
# OR
source myenv/bin/activate  # On macOS/Linux

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Code Execution
### Generating Data Files
Use the existing data files or create a new **LeetCode.xlsx** dataset:
```bash
python scraper.py
```
This script scrapes LeetCode questions and saves them in **LeetCode.xlsx**.
We also support the **MBPP dataset** in JSONL format.

### Running the LLM for Code Generation
To generate responses using an LLM, run:
```bash
python LLMPrompt.py <model> -k <apiKey> -d <dataSource> -o
```
#### Parameters:
- `<model>` – One of the supported models listed above.
- `-k <apiKey>` – OpenAI or Gemini API key (optional if set as an environment variable).
- `-d <dataSource>` – Can be one of:
  - **`leetcode`** – Uses `LeetCode.xlsx` as input.
  - **`mbpp`** – Uses `mbpp.jsonl` dataset.
  - **`user`** – Prompts the user to manually enter a question and test cases in the terminal.
- `-o` – Specifies if the order of the solution is relevant. If order does not matter, include `-o`.

#### Example:
```bash
python LLMPrompt.py "gpt-3.5-turbo" -k "yourAPIKeyGoesHere" -d leetcode -o
```
#### Outputs:
- `ResponseList.csv` – Contains response analysis
- `ResponseLog.txt` – Logs terminal output
- `Solutions/` – Stores generated solutions, organized by question

## Project Structure
### Folders
- **`ImagesAndGraphs/`** – Contains generated graphs and visualizations.
- **`Solutions/`** – Stores LLM-generated solutions categorized by question.

### Key Files
- **`importsCheck.py`** – Installs missing dependencies found in LLM-generated code.
- **`testCaseParser.py`** – Converts test cases from strings to Python data types dynamically.
- **`validation.py`** – Submits LLM-generated solutions to the LeetCode platform.
- **`chartCreation.ipynb`** – Generates plots based on obtained solutions.
- **`computeAcceptancerates.ipynb`** – Computes acceptance rates for interpreted and submitted solutions.
- **`computePromptTokenTime.ipynb`** – Analyzes prompt token lengths and execution times.
- **`responseToken.py`** – Calculates response token lengths.
- **`LeetCode.xlsx`** – Data file containing scraped LeetCode questions.

---

This framework automates the process of generating, testing, and refining code using LLMs, streamlining development and analysis. 🚀

