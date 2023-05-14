import joblib
import openai

import askai

# shared across processes with local file
memory = joblib.Memory(askai.config.cache_path, verbose=0)


@memory.cache
def gpt(prompt: str, *, t: float = 1.0) -> str:
    response = openai.ChatCompletion.create(
        model=askai.config.model,
        messages=[
            {'role': 'user', 'content': prompt},
        ],
        temperature=t,
    )
    askai.config.update_session_tokens(response)
    return response['choices'][0]['message']['content'].strip()
