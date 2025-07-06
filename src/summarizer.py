import os
from typing import Dict
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")


def summarize_and_classify(content: str) -> Dict[str, str]:
    if not openai.api_key:
        return {
            "summary": "",
            "category": "",
            "sentiment": "",
        }
    prompt = (
        "あなたは優秀なカスタマーサポートエージェントです。"\
        "以下のメール内容を要約し、カテゴリと感情を判定してください。"\
        "\n\nメール:\n" + content
    )
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    text = response["choices"][0]["message"]["content"]
    # Expect the model to return JSON-like lines
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
    return result
