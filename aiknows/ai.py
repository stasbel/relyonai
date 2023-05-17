import logging
from typing import Any

import joblib
import openai

from aiknows import config
from aiknows import prompt as ak_prompt
from aiknows import runtime as ak_runtime
from aiknows import utils

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
    config.update_tokens(response)

    code = response['choices'][0]['message']['content'].strip()

    return code


class Session:
    def __init__(self, chat, runtime) -> None:
        super().__init__()

        self.chat = chat
        self.runtime = runtime
        self.reuse = False

    def ai(self, task: str, **kwargs) -> Any:
        self.chat.add_user_task(task, self.reuse, **kwargs)
        self.chat.log_last_message(logging.INFO)
        self.reuse = True  # enabling same runtime afterwards

        result, last_error, history_len = None, None, 0
        while True:
            code = _generate_or_retrieve_code(self.chat.messages)

            try:
                # chat is common to not follow rules all the time
                code = self.chat.strip_code_markdown(code)

                result = self.runtime.run(code)
            except Exception as e:
                self.chat.add_assistant(code)
                self.chat.log_last_message(logging.INFO)

                if isinstance(e, ak_runtime.FinishTaskOKSignal):
                    result = e.result
                    break

                if isinstance(e, ak_runtime.FinishTaskErrorSignal):
                    if e.error_cause:
                        raise e from last_error
                    else:
                        raise e

                self.chat.add_user_error(e)
                self.chat.log_last_message(logging.INFO)
                last_error = e
            else:
                self.chat.add_assistant(code)
                self.chat.log_last_message(logging.INFO)
                self.chat.add_user_result(result)
                self.chat.log_last_message(logging.INFO)

            history_len += 1
            if history_len == config.history_len_max:
                break

        return result


def ai(task: str, *, save_session: bool = False, **kwargs) -> Any:
    chat = ak_prompt.Chat()
    chat.load_system()
    chat.load_examples()
    # chat.log_all_messages(stdout=True)

    runtime = ak_runtime.LocalRuntime()
    runtime.add_vars(kwargs)

    session = Session(chat, runtime)

    result = session.ai(task, **kwargs)

    if save_session:
        return result, session
    else:
        return result
