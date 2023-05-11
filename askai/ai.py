import logging
from typing import Any

import joblib
import openai

import askai
from askai import prompt, utils

logger = logging.getLogger(__name__)

# shared across processes with local file
memory = joblib.Memory(askai.CACHE_DIR, verbose=0)


@memory.cache
def _generate_or_retrieve_code(prompt_messages):
    logger.info('cache miss, generating bytecode')

    response = openai.ChatCompletion.create(
        model=askai.OPENAI_MODEL,
        messages=prompt_messages,
        temperature=0.0,  # maximum truth and less randomness
    )
    code = response['choices'][0]['message']['content'].strip()
    logger.info(f'code: {code}')

    code = code.split('\n')
    if code[0] != '```python' or code[-1] != '```':
        raise ValueError(f'invalid code block response from {askai.OPENAI_MODEL}')
    code = '\n'.join(code[1:-1]).strip()

    return code


def ai(task: str, **kwargs) -> Any:
    prompt_messages = prompt.make_prompt_messages(task, **kwargs)
    logger.info(f'len prompt messages: {len(prompt_messages)}')

    if utils.package_exists('tiktoken'):
        import tiktoken

        tokenizer = tiktoken.encoding_for_model(askai.OPENAI_MODEL)
        prompt_len = len(tokenizer.encode('\n'.join(m['content'] for m in prompt_messages)))
        logger.info(f'prompt length: {prompt_len}')

    # hoping for a cache hit
    code = _generate_or_retrieve_code(prompt_messages)

    # * bytecode isn't pickable by joblib (though we can parse ast first)
    # https://docs.python.org/3/library/functions.html#compile
    bytecode = compile(code, '<gpt>', 'exec')

    # https://docs.python.org/3/library/functions.html#exec
    _globals = kwargs
    exec(bytecode, _globals)
    return _globals['result']
