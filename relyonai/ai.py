import logging
from typing import Any, List

from relyonai import config
from relyonai import llm as roi_llm
from relyonai import prompt as roi_prompt
from relyonai import runtime as roi_runtime
from relyonai import utils as roi_utils

logger = logging.getLogger(__name__)


class Session:
    def __init__(self, prompt, runtime) -> None:
        super().__init__()

        self.prompt = prompt
        self.runtime = runtime
        self.env = 'new'
        self.examples: List[roi_prompt.Example] = []

    def ai(self, task: str, **kwargs) -> Any:
        """refer to :func:`relyonai.ai`"""

        task_example = roi_prompt.Example(task[:10] + '...')
        task_example.add_user_task(task, self.env, kwargs, add_cot=False)
        task_example.log_last(logging.INFO)

        if self.env == 'new':
            self.runtime.clear()
            self.runtime.add_vars(kwargs)
            self.env = 'same'  # enabling same runtime afterwards

        result, last_error, history_len, is_finished_ok = None, None, 0, False
        while True:
            relevant_prompt = self.prompt.fill_up_to_n_tokens(
                example=task_example,
                n_tokens=config.n_tokens_relevant_prompt,
            )
            relevant_prompt.examples.extend(self.examples)
            relevant_prompt.examples.append(task_example)

            response = roi_llm.codegen_gpt(relevant_prompt.messages)

            try:
                code = task_example.parse_code(response)
            except (SyntaxError, roi_runtime.ResponseFormatError) as e:
                task_example.add_assistant(response)
                task_example.log_last(logging.INFO)
                task_example.add_user_error(e)
                task_example.log_last(logging.INFO)
                continue

            task_example.add_assistant(code, add_markdown=True)
            task_example.log_last(logging.INFO)

            try:
                result = self.runtime.run(code)
            except roi_runtime.FinishTaskOKSignal as e:
                result = e.result
                self.runtime.add_vars({'_': result})
                is_finished_ok = True
                break
            except roi_runtime.FinishTaskErrorSignal as e:
                finish_e = roi_runtime.InvalidTaskError(e.message)
                if e.error_cause:
                    raise finish_e from last_error
                else:
                    raise finish_e
            except Exception as e:
                task_example.add_user_error(e, at_runtime=True, code=code)
                task_example.log_last(logging.INFO)
                last_error = e
            else:  # valid code, no finish signals
                task_example.add_user_result(result)
                task_example.log_last(logging.INFO)

            history_len += 1
            if history_len == config.history_len_max:
                break

        self.examples.append(task_example)

        if not is_finished_ok:  # the only option is meeting history limit
            raise roi_runtime.HistroyLimitError('limit of %d reached' % config.history_len_max)

        # finish task ok
        return result


def ai(task: str, *, save_session: bool = False, **kwargs) -> Any:
    """Generates a python object from a task description and given arguments.

    Args:
        task (str): A task description in natural language.
        save_session (bool, optional): True if returns session for preservin runtime state.
          Defaults to False.

    Raises:
        InvalidTaskError: When gpt assistant mark the task as invalid.
        HistroyLimitError: When number of back & forth messages reached `config.history_len_max`.

    Returns:
        Any: Python object generated by the assistant's code.

    """

    prompt = roi_prompt.Prompt.load()
    # prompt.log(logging.INFO)
    # prompt.log(stdout=True)

    source_file_path = None
    if not roi_utils.is_inside_jupyter():
        source_file_path = roi_utils.get_above_caller_file_path()
    runtime = roi_runtime.LocalRuntime(source_file_path=source_file_path)
    runtime.add_vars(kwargs)

    session = Session(prompt, runtime)

    result = session.ai(task, **kwargs)

    if save_session:
        return result, session
    else:
        return result
