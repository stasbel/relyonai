import logging
from typing import Any

from aiknows import config
from aiknows import llm as ak_llm
from aiknows import prompt as ak_prompt
from aiknows import runtime as ak_runtime

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, prompt, runtime) -> None:
        super().__init__()

        self.prompt = prompt
        self.runtime = runtime
        self.env = 'new'

    def ai(self, task: str, **kwargs) -> Any:
        task_example = ak_prompt.Example(task)
        task_example.add_user_task(task, self.env, **kwargs)
        task_example.log_last(logging.INFO, post_nl=True)

        if self.env == 'new':
            self.runtime.clear()
            self.runtime.add_vars(kwargs)
            self.env = 'same'  # enabling same runtime afterwards

        # what are possible reasons of cycle end?
        # controllabel
        # - history limit => raise `FinishTaskErrorSignal` ❌
        # - finish task ok => return result ✅
        # - finish task error => raise `FinishTaskErrorSignal` ❌
        # uncontrollable
        # - ak_llm (openai) error => raise error ❌
        # - any other error => raise error ❌

        result, last_error, history_len, is_finished_ok = None, None, 0, False
        while True:
            relevant_prompt = self.prompt.fill_up_to_n_tokens(
                example=task_example,
                n_tokens=config.n_tokens_relevant_prompt,
            )
            relevant_prompt.add_example(task_example)

            code = ak_llm.generate_or_retrieve_code(relevant_prompt.messages)

            try:
                clean_code = task_example.strip_code_markdown(code)  # could raise error
                result = self.runtime.run(clean_code)
            except Exception as e:
                task_example.add_assistant(code)  # put original code (w/ errors)
                task_example.log_last(logging.INFO, post_nl=True)

                if isinstance(e, ak_runtime.FinishTaskOKSignal):
                    result = e.result
                    is_finished_ok = True
                    break

                if isinstance(e, ak_runtime.FinishTaskErrorSignal):
                    if e.error_cause:
                        raise e from last_error
                    else:
                        raise e

                # no signal => real execution error
                task_example.add_user_error(e)
                task_example.log_last(logging.INFO, post_nl=True)
                last_error = e
            else:
                task_example.add_assistant(code)
                task_example.log_last(logging.INFO, post_nl=True)
                task_example.add_user_result(result)
                task_example.log_last(logging.INFO, post_nl=True)

            history_len += 1
            if history_len == config.history_len_max:
                break

        self.prompt.add_example(task_example)

        if not is_finished_ok:  # the only option is meeting history limit
            raise ak_runtime.FinishTaskErrorSignal(
                'encounting history limit of %d' % config.history_len_max
            )

        # finish task ok
        return result


def ai(task: str, *, save_session: bool = False, **kwargs) -> Any:
    prompt = ak_prompt.Prompt.load()
    # prompt.log(logging.INFO)
    # prompt.log(stdout=True)

    runtime = ak_runtime.LocalRuntime()
    runtime.add_vars(kwargs)

    session = Session(prompt, runtime)

    result = session.ai(task, **kwargs)

    if save_session:
        return result, session
    else:
        return result
