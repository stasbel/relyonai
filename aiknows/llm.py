import logging
from typing import List

import joblib
import openai

from aiknows import config

DEFAULT_TEMPERATURE = 1.0

logger = logging.getLogger(__name__)

# shared across processes with local file
memory = joblib.Memory(config.cache_path, verbose=0)


@memory.cache
def generate_or_retrieve_code(prompt_messages):
    logger.info('cache miss on generating code')
    if config.dollars_spent > config.dollars_limit:
        raise ValueError('dollars limit exceeded')

    logger.info(f'len prompt messages: {len(prompt_messages)}')
    response = openai.ChatCompletion.create(
        model=config.model,
        messages=prompt_messages,
        temperature=0.0,  # maximum truth, minimum randomness
    )
    total_tokens = response['usage']['total_tokens']
    logger.info(f'real prompt token length: {total_tokens}')
    config.update_tokens(response)

    code = response['choices'][0]['message']['content'].strip()

    return code


@memory.cache
def gpt(prompt: str, *, t: float = DEFAULT_TEMPERATURE) -> str:
    logger.info('cache miss on gpt')
    if config.dollars_spent > config.dollars_limit:
        raise ValueError('dollars limit exceeded')

    response = openai.ChatCompletion.create(
        model=config.model,
        messages=[
            {'role': 'user', 'content': prompt},
        ],
        temperature=t,
    )
    config.update_tokens(response)
    return response['choices'][0]['message']['content'].strip()


@memory.cache
async def agpt(prompt: str, *, t: float = DEFAULT_TEMPERATURE) -> str:
    del prompt
    del t
    raise NotImplementedError('although it\'s very simple')


@memory.cache
def emb(text: str) -> List[float]:
    logger.info('cache miss on emb')
    if config.dollars_spent > config.dollars_limit:
        raise ValueError('dollars limit exceeded')

    # https://github.com/openai/openai-python/blob/da828789387755c964c8816d1198d9a61df85b2e/openai/embeddings_utils.py#L20
    text = text.replace('\n', ' ')

    response = openai.Embedding.create(
        model=config.embedding_model,
        input=text,
    )
    config.update_embedding_tokens(response)

    emb = response['data'][0]['embedding']

    return emb
