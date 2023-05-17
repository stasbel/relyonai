import logging

import joblib
import openai

from aiknows import config, utils

DEFAULT_TEMPERATURE = 1.0

logger = logging.getLogger(__name__)

# shared across processes with local file
memory = joblib.Memory(config.cache_path, verbose=0)


@memory.cache
def generate_or_retrieve_code(prompt_messages):
    if config.dollars_spent > config.dollars_limit:
        raise ValueError('dollars limit exceeded')

    logger.info('cache miss, generating bytecode')
    logger.info(f'len prompt messages: {len(prompt_messages)}')

    if utils.package_exists('tiktoken'):
        import tiktoken

        tokenizer = tiktoken.encoding_for_model(config.model)
        prompt_token_len = len(tokenizer.encode('\n'.join(m['content'] for m in prompt_messages)))
        logger.info(f'estimate prompt token length: {prompt_token_len}')

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
