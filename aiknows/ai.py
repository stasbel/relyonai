import logging
from typing import Any

from aiknows import config
from aiknows import llm as ak_llm
from aiknows import prompt as ak_prompt
from aiknows import runtime as ak_runtime

logger = logging.getLogger(__name__)


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
            code = ak_llm.generate_or_retrieve_code(self.chat.messages)

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
