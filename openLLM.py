from unsloth import FastLanguageModel
from transformers import TextStreamer, pipeline
from unsloth.chat_templates import get_chat_template
import regex as re
import torch


def extract_python_code(code):
    code_only = re.findall(r"```python\n(.*?)```", code, re.DOTALL)
    return code_only[-1] if code_only else code # Returns the last solution suggested by the model based on CoT


def extract_after_end_header(response):
    parts = response.rsplit("<|end_header_id|>", 1)
    return parts[-1].strip() if len(parts) > 1 else response.strip()


def get_llm_response(model, messages):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = model, #"unsloth/Llama-3.2-1B-Instruct-bnb-4bit",
        max_seq_length = 128000, # set to max 
        load_in_4bit = True,
    )
    tokenizer = get_chat_template(
        tokenizer,
        chat_template = "llama-3.1",
    )
    FastLanguageModel.for_inference(model)
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # Tokenizing the prompt to calculate token length
    prompt_tokens = tokenizer.encode(prompt)
    prompt_token_length = len(prompt_tokens)

    response = pipe(prompt, max_new_tokens = 32768, temperature = 1, use_cache = True)
    # Tokenizing the generated response to calculate token length
    generated_text = response[0]["generated_text"]
    response_tokens = tokenizer.encode(generated_text)
    response_token_length = len(response_tokens) - prompt_token_length # To calculate only the token lengths of the response generated

    solution = extract_after_end_header(generated_text)

    return extract_python_code(solution), prompt_token_length, response_token_length
