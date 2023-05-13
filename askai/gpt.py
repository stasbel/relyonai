import joblib
import openai

import askai

# shared across processes with local file
memory = joblib.Memory(askai.CACHE_DIR, verbose=0)


@memory.cache
def gpt(prompt: str, *, t: float = 1.0) -> str:
    response = openai.ChatCompletion.create(
        model=askai.OPENAI_MODEL,
        messages=[
            {'role': 'user', 'content': prompt},
        ],
        temperature=t,
    )
    return response['choices'][0]['message']['content'].strip()
