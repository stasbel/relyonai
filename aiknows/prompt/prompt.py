import json
import logging
import os
import traceback

from aiknows import config
from aiknows import explain as ak_explain

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)


class Chat:
    # refer to SCHEMA.md for the format

    def __init__(self, add_example_names=False):
        super().__init__()

        self.messages = []
        self.add_example_names = add_example_names

    def load_system(self):
        with open(os.path.join(CURRENT_DIR, 'system.txt')) as f:
            content = f.read().format(python_version=config.python_version)

        self.messages.append(
            {
                'role': 'system',
                'content': content,
            }
        )

    def load_examples(self):
        self.load('examples/examples.json')

    def wrap_example_name(self, role, content):
        if self.add_example_names:
            # https://github.com/openai/openai-python/blob/main/chatml.md#few-shot-prompting
            return {
                'role': 'system',
                'name': f'example_{role}',
                'content': content,
            }
        else:
            return {
                'role': role,
                'content': content,
            }

    def add_user_task(self, task, reuse, **kwargs):
        schema = 'TASK: """\n{task}\n"""\nREUSE: {reuse}\nARGS: {args_list}\n{args_explanations}'
        args_list_repr = '[' + ', '.join(kwargs.keys()) + ']'
        args_explanations = []
        for k, v in kwargs.items():
            v_explanation = ak_explain.explain(v)
            if len(v_explanation) > config.n_truncate_repr:
                logger.warning('truncating explanation to %d chars', config.n_truncate_repr)
                v_explanation = v_explanation[: config.n_truncate_repr] + '...[truncated]'

            args_explanations.append(f'- {k}: """\n{v_explanation}\n"""')

        content = schema.format(
            task=task,
            reuse=reuse,
            args_list=args_list_repr,
            args_explanations='\n'.join(args_explanations),
        ).strip()

        self.messages.append(self.wrap_example_name('user', content))

    def add_user_result(self, result):
        result_repr = repr(result)
        if len(result_repr) > config.n_truncate_repr:
            logger.warning('truncating result repr to %d chars', config.n_truncate_repr)
            result_repr = result_repr[: config.n_truncate_repr] + '...[truncated]'

        content = f'RESULT: """\n{result_repr}\n"""'
        self.messages.append(self.wrap_example_name('user', content))

    def add_user_error(self, error):
        tb = traceback.extract_tb(error.__traceback__)
        last_frame_repr = ''.join(traceback.format_list([tb[-1]])).strip()
        traceback_repr = ''.join(traceback.format_exception_only(type(error), error)).strip()
        error_repr = f'{last_frame_repr}\n{traceback_repr}'

        if len(error_repr) > config.n_truncate_repr:
            logger.warning('truncating error repr to %d chars', config.n_truncate_repr)
            error_repr = error_repr[: config.n_truncate_repr] + '...[truncated]'

        content = f'ERROR: """\n{error_repr}\n"""'
        self.messages.append(self.wrap_example_name('user', content))

    @staticmethod
    def add_code_markdown(code):
        return f'```python\n{code}\n```'

    @staticmethod
    def strip_code_markdown(code):
        code = code.split('\n')
        if code[0] != '```python' or code[-1] != '```':
            raise ValueError(
                'code block format is invalid: make sure assistant response'
                ' starts with "```python", ends with "```" and have valid python code inside'
            )
        code = '\n'.join(code[1:-1]).strip()
        return code

    def add_assistant(self, code):
        content = self.add_code_markdown(code)
        self.messages.append(self.wrap_example_name('assistant', content))

    def save(self, path):
        with open(os.path.join(CURRENT_DIR, path), 'w') as f:
            json.dump(self.messages, f)

    def load(self, path):
        with open(os.path.join(CURRENT_DIR, path), 'r') as f:
            self.messages.extend(json.load(f))

    @staticmethod
    def message_repr(message, nlx, nly):
        return '# {role}{name}{nlxs}{content}{nlys}'.format(
            role=message['role'],
            name=f' name={message["name"]}' if 'name' in message else '',
            nlxs='\n' * nlx,
            content=message['content'],
            nlys='\n' * nly,
        )

    def log_last_message(self, level=None, *, stdout=False):
        assert level is not None or stdout
        message = self.messages[-1]
        if stdout:
            print(self.message_repr(message, 2, 1))
        else:
            logger.log(level, self.message_repr(message, 1, 0))

    def log_all_messages(self, level=None, *, stdout=False):
        assert level is not None or stdout
        for message in self.messages:
            if stdout:
                print(self.message_repr(message, 2, 1))
            else:
                logger.log(level, self.message_repr(message, 1, 0))
