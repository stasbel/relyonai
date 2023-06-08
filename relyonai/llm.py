import logging
from typing import Dict, List

import joblib
import openai
import tenacity

from relyonai import config
from relyonai import runtime as ak_runtime

DEFAULT_TEMPERATURE = 1.0

logger = logging.getLogger(__name__)

# shared across processes with local file
memory = joblib.Memory(config.cache_path, verbose=0)


@memory.cache
@tenacity.retry(
    wait=tenacity.wait_random_exponential(min=1, max=20),
    stop=tenacity.stop_after_attempt(3),
)
def _cached_codegen_gpt(model, prompt_messages):
    logger.info('cache miss on codegen gpt')
    if config.dollars_spent > config.dollars_limit:
        raise ak_runtime.DollarsLimitError(f'{config.dollars_limit}$ limit met')

    logger.info(f'len prompt messages: {len(prompt_messages)}')
    response = openai.ChatCompletion.create(
        model=model,
        messages=prompt_messages,
        temperature=0.0,  # it's code: maximum truth, minimum randomness
        stop=['```\n', '```<|endoftext|>'],
    )

    total_tokens = response['usage']['total_tokens']
    logger.info(f'codegen token usage: {total_tokens}')
    config.update_tokens(response)

    result = response['choices'][0]['message']['content'].strip() + '```'

    return result


def codegen_gpt(prompt_messages: List[Dict[str, str]]) -> str:
    return _cached_codegen_gpt(config.model, prompt_messages)


@memory.cache
@tenacity.retry(
    wait=tenacity.wait_random_exponential(min=1, max=20),
    stop=tenacity.stop_after_attempt(3),
)
def _cached_gpt(model, prompt, temperature):
    logger.info('cache miss on gpt')
    if config.dollars_spent > config.dollars_limit:
        raise ak_runtime.DollarsLimitError(f'{config.dollars_limit}$ limit met')

    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {'role': 'user', 'content': prompt},
        ],
        temperature=temperature,
    )

    total_tokens = response['usage']['total_tokens']
    logger.info(f'gpt token usage: {total_tokens}')
    config.update_tokens(response)

    result = response['choices'][0]['message']['content'].strip()

    return result


def gpt(prompt: str, *, t: float = DEFAULT_TEMPERATURE) -> str:
    """Text completion with GPT model.

    Args:
        prompt (str): A string to be completed.
        t (float, optional): Temperature in range [0.0, 2.0]. Defaults to DEFAULT_TEMPERATURE.

    Raises:
        ValueError: _description_

    Returns:
        str: _description_
    """

    return _cached_gpt(config.model, prompt, t)


@memory.cache
@tenacity.retry(
    wait=tenacity.wait_random_exponential(min=1, max=20),
    stop=tenacity.stop_after_attempt(3),
)
def _cahed_emb(model, text):
    logger.info('cache miss on emb')
    if config.dollars_spent > config.dollars_limit:
        raise ak_runtime.DollarsLimitError(f'{config.dollars_limit}$ limit met')

    # https://github.com/openai/openai-python/blob/da828789387755c964c8816d1198d9a61df85b2e/openai/embeddings_utils.py#L20
    text = text.replace('\n', ' ')

    response = openai.Embedding.create(
        model=model,
        input=text,
    )

    total_tokens = response['usage']['total_tokens']
    logger.info(f'emb token usage: {total_tokens}')
    config.update_tokens(response)

    result = response['data'][0]['embedding']

    return result


def emb(text: str) -> List[float]:
    """_summary_

    Args:
        text (str): _description_

    Returns:
        List[float]: _description_
    """

    return _cahed_emb(config.embedding_model, text)
