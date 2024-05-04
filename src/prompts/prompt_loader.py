import os
import json

def load_prompt_by_language(language: str) -> dict:
    json_path = os.path.join('prompts','translations', f'{language}.json')
    with open(json_path, 'r') as translations:
        prompts = json.load(translations, strict=False)
    return prompts