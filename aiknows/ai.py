import logging
from typing import Any

import joblib
import openai

from aiknows import config, prompt, runtime, utils

logger = logging.getLogger(__name__)

# shared across processes with local file
memory = joblib.Memory(config.cache_path, verbose=0)


@memory.cache
def _generate_or_retrieve_code(prompt_messages):
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
    config.update_session_tokens(response)

    code = response['choices'][0]['message']['content'].strip()

    return code


def ai(task: str, *, save_runtime: bool = False, **kwargs) -> Any:
    runtime.throw_signals = True
    local_runtime = runtime.LocalRuntime()
    local_runtime.add_vars(kwargs)

    chat = prompt.Chat()
    chat.add_system()
    # chat.log_last(logging.INFO)
    chat.load('examples')
    chat.add_user_task(task, False, **kwargs)
    chat.log_last(logging.INFO)
    # chat.print()

    result, last_error, history_len = None, None, 0
    while True:
        code = _generate_or_retrieve_code(chat.messages)

        try:
            # we don't redirect stdout/stderr as we want to feel as natural as possible
            result = local_runtime.run(code)
        except Exception as e:
            chat.add_assistant(code)
            chat.log_last(logging.INFO)

            if isinstance(e, runtime.FinishTaskOKSignal):
                result = e.result
                break

            if isinstance(e, runtime.FinishTaskErrorSignal):
                if e.error_cause:
                    raise e from last_error
                else:
                    raise e

            chat.add_user_error(e)
            chat.log_last(logging.INFO)
            last_error = e
        else:
            chat.add_assistant(code)
            chat.log_last(logging.INFO)
            chat.add_user_result(result)
            chat.log_last(logging.INFO)
            local_runtime.add_vars({'_': result})

        history_len += 1
        if history_len == config.history_len_max:
            break

    return result
