import joblib
import openai

import aiknows

# shared across processes with local file
memory = joblib.Memory(aiknows.config.cache_path, verbose=0)


@memory.cache
def gpt(prompt: str, *, t: float = 1.0) -> str:
    response = openai.ChatCompletion.create(
        model=aiknows.config.model,
        messages=[
            {'role': 'user', 'content': prompt},
        ],
        temperature=t,
    )
    aiknows.config.update_session_tokens(response)
    return response['choices'][0]['message']['content'].strip()
