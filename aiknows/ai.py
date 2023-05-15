import logging
from typing import Any

import joblib
import openai

import aiknows
from aiknows import prompt, runtime, utils

logger = logging.getLogger(__name__)

# shared across processes with local file
memory = joblib.Memory(aiknows.config.cache_path, verbose=0)


@memory.cache
def _generate_or_retrieve_code(prompt_messages):
    logger.info('cache miss, generating bytecode')
    logger.info(f'len prompt messages: {len(prompt_messages)}')

    if utils.package_exists('tiktoken'):
        import tiktoken

        tokenizer = tiktoken.encoding_for_model(aiknows.config.model)
        prompt_token_len = len(tokenizer.encode('\n'.join(m['content'] for m in prompt_messages)))
        logger.info(f'estimate prompt token length: {prompt_token_len}')

    response = openai.ChatCompletion.create(
        model=aiknows.config.model,
        messages=prompt_messages,
        temperature=0.0,  # maximum truth, minimum randomness
    )
    total_tokens = response['usage']['total_tokens']
    logger.info(f'real prompt token length: {total_tokens}')
    aiknows.config.update_session_tokens(response)

    code = response['choices'][0]['message']['content'].strip()

    code = code.split('\n')
    if code[0] != '```python' or code[-1] != '```':
        raise ValueError(f'invalid code block response from {aiknows.config.model}')
    code = '\n'.join(code[1:-1]).strip()

    return code


def ai(task: str, *, save_runtime: bool = False, **kwargs) -> Any:
    if set(kwargs.keys()) & set(runtime.REVERSVED_KEYWORDS):
        raise ValueError(f'reserved keywords: {runtime.REVERSVED_KEYWORDS}')

    chat = prompt.Chat()
    chat.add_system()
    chat.load('examples')
    chat.add_user_task(task, **kwargs)

    globals = kwargs.copy()
    globals['gpt'] = aiknows.gpt
    globals['AIKnowsTaskError'] = runtime.FinishTaskErrorSignal

    last_raised_exception, history_len = None, 0
    while True:
        # hoping for a cache hit
        code = _generate_or_retrieve_code(chat.messages)
        chat.add_assistant(code)
        logger.info(f'assistant: {chat.messages[-1]["content"]}')

        try:
            # https://docs.python.org/3/library/functions.html#compile
            # * bytecode isn't pickable by joblib (though we can parse ast first)
            # bytecode = compile(code, '<gpt>', 'exec')

            # https://docs.python.org/3/library/functions.html#exec
            # * we don't redirect stdout/stderr as we want to feel as natural as possible
            exec(code, globals)
        except Exception as e:
            if isinstance(e, AIKnowsTaskError):
                if e.error_cause:
                    raise e from last_raised_exception
                else:
                    raise e

            # set last exception for that runtime
            last_raised_exception = e

            chat.add_user_error(e)
            logger.info(f'user/error: {chat.messages[-1]["content"]}')
        else:
            if 'final_result' in globals:
                break

            chat.add_user_result(globals['result'])
            logger.info(f'user/result: {chat.messages[-1]["content"]}')

        history_len += 1
        if history_len == aiknows.config.history_len_max:
            break

    return globals['final_result']