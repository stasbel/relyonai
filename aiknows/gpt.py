import joblib
import openai

from aiknows import config

DEFAULT_TEMPERATURE = 1.0

# shared across processes with local file
memory = joblib.Memory(config.cache_path, verbose=0)


@memory.cache
def gpt(prompt: str, *, t: float = DEFAULT_TEMPERATURE) -> str:
    response = openai.ChatCompletion.create(
        model=config.model,
        messages=[
            {'role': 'user', 'content': prompt},
        ],
        temperature=t,
    )
    config.update_session_tokens(response)
    return response['choices'][0]['message']['content'].strip()


@memory.cache
async def agpt(prompt: str, *, t: float = DEFAULT_TEMPERATURE) -> str:
    del prompt
    del t
    raise NotImplementedError('although it\'s very simple')
