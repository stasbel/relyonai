import logging
from typing import Any

from aiknows import config
from aiknows import llm as ak_llm
from aiknows import prompt as ak_prompt
from aiknows import runtime as ak_runtime
from aiknows import utils as ak_utils

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, prompt, runtime) -> None:
        super().__init__()

        self.prompt = prompt
        self.runtime = runtime
        self.env = 'new'
        self.examples = []

    def ai(self, task: str, **kwargs) -> Any:
        task_example = ak_prompt.Example(task[:10] + '...')
        task_example.add_user_task(task, self.env, kwargs)
        task_example.log_last(logging.INFO, post_nl=True)

        if self.env == 'new':
            self.runtime.clear()
            self.runtime.add_vars(kwargs)
            self.env = 'same'  # enabling same runtime afterwards

        # what are possible reasons of cycle end?
        # controllable
        # - finish task ok => return result ✅
        # - finish task error => raise `ak_runtime.InvalidTaskError` ❌
        # - history limit => raise `ak_runtime.HistroyLimitError` ❌
        # uncontrollable
        # - ak_llm (openai) error => raise error ❌
        # - strip_code_markdown error => raise error ❌
        # - any other error => raise error ❌

        result, last_error, history_len, is_finished_ok = None, None, 0, False
        while True:
            relevant_prompt = self.prompt.fill_up_to_n_tokens(
                example=task_example,
                n_tokens=config.n_tokens_relevant_prompt,
            )
            relevant_prompt.examples.extend(self.examples)
            relevant_prompt.examples.append(task_example)

            response = ak_llm.generate_or_retrieve_code(relevant_prompt.messages)
            task_example.add_assistant(response)
            task_example.log_last(logging.INFO, post_nl=True)

            try:
                code = task_example.strip_code_markdown(response)  # could raise error
                result = self.runtime.run(code)
            except Exception as e:
                if isinstance(e, ak_runtime.FinishTaskOKSignal):
                    self.runtime.add_vars({'_': e.result})
                    result = e.result
                    is_finished_ok = True
                    break

                if isinstance(e, ak_runtime.FinishTaskErrorSignal):
                    finish_e = ak_runtime.InvalidTaskError(e.message)
                    if e.error_cause:
                        raise finish_e from last_error
                    else:
                        raise finish_e

                # response format is incorrect
                if isinstance(e, ak_runtime.ResponseFormatError):
                    task_example.add_user_error(e)
                    task_example.log_last(logging.INFO, post_nl=True)
                    continue

                # python code is invalid
                if isinstance(e, SyntaxError):
                    task_example.add_user_error(e, at_parsing=True, code=code)
                    task_example.log_last(logging.INFO, post_nl=True)
                    continue

                # real execution error
                task_example.add_user_error(e, at_runtime=True, code=code)
                task_example.log_last(logging.INFO, post_nl=True)
                last_error = e
            else:
                task_example.add_user_result(result)
                task_example.log_last(logging.INFO, post_nl=True)

            history_len += 1
            if history_len == config.history_len_max:
                break

        # self.prompt.add_example(task_example)
        self.examples.append(task_example)

        if not is_finished_ok:  # the only option is meeting history limit
            raise ak_runtime.HistroyLimitError('limit of %d reached' % config.history_len_max)

        # finish task ok
        return result


def ai(task: str, *, save_session: bool = False, **kwargs) -> Any:
    prompt = ak_prompt.Prompt.load()
    # prompt.log(logging.INFO)
    # prompt.log(stdout=True)

    source_file_path = None
    if not ak_utils.is_inside_jupyter():
        source_file_path = ak_utils.get_above_caller_file_path()
    runtime = ak_runtime.LocalRuntime(source_file_path=source_file_path)
    runtime.add_vars(kwargs)

    session = Session(prompt, runtime)

    result = session.ai(task, **kwargs)

    if save_session:
        return result, session
    else:
        return result
