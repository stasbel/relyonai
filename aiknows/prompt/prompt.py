import json
import logging
import os
import traceback

import tiktoken

from aiknows import config
from aiknows import explain as ak_explain
from aiknows import llm as ak_llm
from aiknows import utils as ak_utils

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)
SYSTEM_DIR = os.path.join(CURRENT_DIR, 'system')
DEFAULT_SYSTEM_FILE = 'default.md'
DEFAULT_PROMPT_FILE = 'prompt.json'


class Example:
    # refer to NEW_SCHEMA.md for the format

    def __init__(self, name=None, *, add_example_names=False, data=None):
        super().__init__()

        self.name = name
        self.add_example_names = add_example_names
        self.data = data or []

    @property
    def messages(self):
        result = []
        for data in self.data:
            data = data.copy()
            data.pop('task', None)
            result.append(data)

        return result

    @property
    def n_tokens(self):
        tokenizer = tiktoken.encoding_for_model(config.model)
        prompt_token_len = len(tokenizer.encode(repr(self)))
        return prompt_token_len

    @property
    def emb(self):
        # return ak_llm.emb(repr(self))
        tasks_repr = '\n'.join(data['task'] for data in self.data if 'task' in data)
        return ak_llm.emb(tasks_repr)

    MESSAGE_SCHEMA = '==={role}{name}===\n\n{content}'

    def data_repr(self, data):
        name_repr = f' {data["name"]}' if 'name' in data else ''
        return self.MESSAGE_SCHEMA.format(
            role=data['role'],
            name=name_repr,
            content=data['content'],
        )

    def __repr__(self) -> str:
        data_reprs = []
        for data in self.data:
            data_reprs.append(self.data_repr(data))

        return '\n\n'.join(data_reprs)

    def construct_message(self, role, content):
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

    USER_TASK_SCHEMA = 'TASK: """\n{task}\n"""\nENV: {env}\nARGS: {args}'

    def add_user_task(self, task, env, **kwargs):
        # env_repr = f'\'{env}\''
        env_repr = env
        args_repr = []
        for k, v in kwargs.items():
            v_explanation = ak_explain.explain(v)
            if len(v_explanation) > config.n_truncate_repr:
                logger.warning('truncating explanation to %d chars', config.n_truncate_repr)
                v_explanation = v_explanation[: config.n_truncate_repr] + '...[truncated]'

            args_repr.append(f'- {k}: """\n{v_explanation}\n"""')
        if len(args_repr) > 0:
            args_repr = '\n' + '\n'.join(args_repr)
        else:
            args_repr = '<empty>'

        content = self.USER_TASK_SCHEMA.format(task=task, env=env_repr, args=args_repr).strip()
        message = self.construct_message('user', content)
        message['task'] = task
        self.data.append(message)

    USER_RESULT_SCHEMA = 'RESULT: """\n{result}\n"""'

    def add_user_result(self, result):
        result_repr = repr(result)
        if len(result_repr) > config.n_truncate_repr:
            logger.warning('truncating result repr to %d chars', config.n_truncate_repr)
            result_repr = result_repr[: config.n_truncate_repr] + '...[truncated]'

        content = self.USER_RESULT_SCHEMA.format(result=result_repr).strip()
        self.data.append(self.construct_message('user', content))

    USER_ERROR_SCHEMA = 'ERROR: """\n{error}\n"""'

    def add_user_error(self, error):
        # tb = traceback.extract_tb(error.__traceback__)
        # last_frame_repr = ''.join(traceback.format_list([tb[-1]])).strip()
        traceback_repr = ''.join(traceback.format_exception_only(type(error), error)).strip()
        # error_repr = f'{last_frame_repr}\n{traceback_repr}'
        error_repr = f'{traceback_repr}'

        if len(error_repr) > config.n_truncate_repr:
            logger.warning('truncating error repr to %d chars', config.n_truncate_repr)
            error_repr = error_repr[: config.n_truncate_repr] + '...[truncated]'

        content = self.USER_ERROR_SCHEMA.format(error=error_repr).strip()
        self.data.append(self.construct_message('user', content))

    @staticmethod
    def add_code_markdown(code):
        return f'```python\n{code}\n```'

    @staticmethod
    def strip_code_markdown(code):
        code = code.split('\n')
        if code[0] != '```python' or code[-1] != '```':
            raise ValueError(
                'assistance response code is of invalid format:'
                ' double check that the code is wrapped in ```python ... ```'
            )
        code = '\n'.join(code[1:-1]).strip()
        return code

    def add_assistant(self, code, add_markdown=False):
        if add_markdown:
            code = self.add_code_markdown(code)

        self.data.append(self.construct_message('assistant', code))

    def log(self, level=None, *, stdout=False):
        assert level is not None or stdout
        full_repr = repr(self)
        if stdout:
            print(full_repr)
        else:
            logger.log(level, full_repr)

    def log_last(self, level=None, *, stdout=False, post_nl=False):
        assert level is not None or stdout
        full_repr = self.data_repr(self.data[-1]) + '\n' * int(post_nl)
        if stdout:
            print(full_repr)
        else:
            logger.log(level, full_repr)


class Prompt:
    SYSTEM_NAME = '<system>'

    def __init__(self, system=None, *, examples=None):
        super().__init__()

        if system is None:
            self.system = self.load_system()
        else:
            self.system = system

        self.examples = examples or []

    def add_example(self, example):
        self.examples.append(example)

    @classmethod
    def load_system(cls, file=DEFAULT_SYSTEM_FILE):
        with open(os.path.join(SYSTEM_DIR, file)) as f:
            content = f.read().format(python_version=config.python_version)

        return Example(cls.SYSTEM_NAME, data=[{'role': 'system', 'content': content}])

    @property
    def messages(self):
        messages = []
        messages.extend(self.system.messages)

        for example in self.examples:
            messages.extend(example.messages)

        return messages

    @property
    def n_tokens(self):
        result = self.system.n_tokens
        for example in self.examples:
            result += example.n_tokens
        return result

    def fill_up_to_n_tokens(self, example, n_tokens) -> 'Prompt':
        k_tokens = n_tokens
        k_tokens -= self.system.n_tokens

        ordered_examples = sorted(
            self.examples,
            key=lambda e: ak_utils.cosine_similarity(e.emb, example.emb),
            reverse=False,  # from least to most
        )

        examples = []
        while k_tokens > 0:
            example = ordered_examples.pop()

            if example.n_tokens > k_tokens:
                break

            examples.append(example)
            k_tokens -= example.n_tokens

        # in prompt we want most similar examples to be first
        examples = list(reversed(examples))

        result = Prompt(system=self.system, examples=examples)
        assert result.n_tokens <= n_tokens

        return result

    def save(self, path=DEFAULT_PROMPT_FILE):
        data = {
            'system': self.system.data,
            'examples': [
                {
                    'name': example.name,
                    'add_example_names': example.add_example_names,
                    'data': example.data,
                }
                for example in self.examples
            ],
        }

        with open(os.path.join(CURRENT_DIR, path), 'w') as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path=DEFAULT_PROMPT_FILE):
        with open(os.path.join(CURRENT_DIR, path), 'r') as f:
            data = json.load(f)

        system = Example(cls.SYSTEM_NAME, data=data['system'])
        examples = []
        for example_data in data['examples']:
            example = Example(
                name=example_data['name'],
                add_example_names=example_data['add_example_names'],
                data=example_data['data'],
            )
            examples.append(example)

        return cls(system=system, examples=examples)

    def log(self, level=None, *, stdout=False):
        assert level is not None or stdout
        examples_reprs = [repr(self.system)]
        for example in self.examples:
            examples_reprs.append(repr(example))

        full_repr = '\n\n'.join(examples_reprs)
        if stdout:
            print(full_repr)
        else:
            logger.log(level, full_repr)
