import ast
import json
import logging
import os
import re

import tiktoken

from relyonai import config
from relyonai import explain as roi_explain
from relyonai import llm as roi_llm
from relyonai import runtime as roi_runtime
from relyonai import utils as roi_utils

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)
SYSTEM_DIR = os.path.join(CURRENT_DIR, 'system')
DEFAULT_SYSTEM_FILE = 'default.md'
DEFAULT_PROMPT_FILE = 'prompt.json'


class Example:
    # refer to NEW_SCHEMA.md for the format

    def __init__(self, name=None, *, add_example_names=False, messages=None, tasks=None):
        super().__init__()

        self.name = name
        self.add_example_names = add_example_names
        self.messages = messages or []
        self.tasks = tasks or []

    @property
    def n_tokens(self):
        tokenizer = tiktoken.encoding_for_model(config.model)
        prompt_token_len = len(tokenizer.encode(repr(self)))
        return prompt_token_len

    @property
    def emb(self):
        # return roi_llm.emb(repr(self))
        # embedding model is confused by all this markdown
        tasks_repr = '\n'.join(self.tasks)
        return roi_llm.emb(tasks_repr)

    MESSAGE_SCHEMA = '==={role}{name}===\n{content}'

    def message_repr(self, message):
        name_repr = f' {message["name"]}' if 'name' in message else ''
        return self.MESSAGE_SCHEMA.format(
            role=message['role'],
            name=name_repr,
            content=message['content'],
        )

    def __repr__(self) -> str:
        message_reprs = []
        for message in self.messages:
            message_reprs.append(self.message_repr(message))

        return '\n'.join(message_reprs)

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

    USER_TASK_SCHEMA = (
        'task description: """\n{task}\n"""\nenvironment: {env}\nglobal variables: {args}'
    )
    COT_PROMPT = 'let’s work this out in a step by step way to be sure we have the right answer'

    def add_user_task(self, task, env, args, *, add_cot=False):
        task_repr = task
        if add_cot:
            # task_repr += f'\ndon\'t create an example code, return objective'
            task_repr += f'\n{self.COT_PROMPT}'

        if env == 'new':
            env_repr = 'new python interpreter'
        elif env == 'same':
            env_repr = 'reused from previous task'
        else:
            raise ValueError(f'invalid env: {env}')

        args_repr = []
        for k, v in args.items():
            v_explanation = roi_explain.explain(v)
            # args_repr.append(f'- {k} ({v_explanation["type"]})')
            # v_explanation.pop('type')
            args_repr.append(f'- {k}')
            # v_explanation.pop('type')
            for k2, v2 in v_explanation.items():
                args_repr.append(f'    - {k2}: {v2}')
        if len(args_repr) > 0:
            args_repr = '\n' + '\n'.join(args_repr)
        else:
            args_repr = '<empty>'

        content = self.USER_TASK_SCHEMA.format(
            task=task_repr,
            env=env_repr,
            args=args_repr,
        ).strip()
        self.messages.append(self.construct_message('user', content))
        self.tasks.append(task)

    USER_RESULT_SCHEMA = 'result: """\n{result}\n"""'

    def add_user_result(self, result):
        result_repr = repr(result)
        if len(result_repr) > config.n_truncate_repr:
            logger.warning('truncating result repr to %d chars', config.n_truncate_repr)
            result_repr = result_repr[: config.n_truncate_repr] + '...[truncated]'

        content = self.USER_RESULT_SCHEMA.format(result=result_repr).strip()
        self.messages.append(self.construct_message('user', content))

    USER_ERROR_SCHEMA = 'error: """\n{error}\n"""'
    HINT_SCHEMA = 'hint: """\n{hint}\n"""'

    def add_user_error(self, error, *, at_runtime=False, code=None):
        error_repr = roi_runtime.LocalRuntime.error_repr(
            error=error,
            at_runtime=at_runtime,
            code=code,
        )
        error_repr = self.USER_ERROR_SCHEMA.format(error=error_repr).strip()

        # this is hacky
        if isinstance(error, ModuleNotFoundError):
            hint_repr = 'try to use python standard library and installed pip packages'
            hint_repr += '\napproach problem differently'
            hint_repr += '\ndo no attempt installing packages'
            error_repr += f'\n{self.HINT_SCHEMA.format(hint=hint_repr)}'
            error_repr = error_repr.strip()

        if len(error_repr) > config.n_truncate_repr:
            logger.warning('truncating error repr to %d chars', config.n_truncate_repr)
            error_repr = error_repr[: config.n_truncate_repr] + '...[truncated]'

        content = error_repr
        self.messages.append(self.construct_message('user', content))

    @staticmethod
    def add_code_markdown(code):
        return f'```python\n{code}\n```'

    @staticmethod
    def parse_code(response):
        pattern = r'```python\n((?:.*\n)*?)```'
        match = re.search(pattern, response, re.MULTILINE)
        if not match:
            raise roi_runtime.ResponseFormatError(
                'wrap code in markdown code block: ```python{{code}}```'
            )

        code = match.group(1).strip()

        # TODO: make this more robust
        ast.parse(code)  # check

        return code

    def add_assistant(self, code, add_markdown=False):
        if add_markdown:
            code = self.add_code_markdown(code)

        self.messages.append(self.construct_message('assistant', code))

    def log(self, level=None, *, stdout=False, post_nl=False):
        assert level is not None or stdout
        full_repr = repr(self) + '\n' * int(post_nl)
        if stdout:
            print(full_repr)
        else:
            logger.log(level, full_repr)

    def log_last(self, level=None, *, stdout=False, post_nl=False):
        assert level is not None or stdout
        full_repr = self.message_repr(self.messages[-1]) + '\n' * int(post_nl)
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

    @classmethod
    def load_system(cls, file=DEFAULT_SYSTEM_FILE):
        with open(os.path.join(SYSTEM_DIR, file)) as f:
            content = f.read()

        # adding python version
        content = content.format(
            python_version=config.python_version,
            python_interpreter=roi_utils.python_intepreter_repr(),
        )

        # https://www.promptingguide.ai/models/chatgpt#instructing-chat-models
        system_role = 'system'
        if config.model != 'gpt-4':
            system_role = 'user'
        return Example(cls.SYSTEM_NAME, messages=[{'role': system_role, 'content': content}])

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
            key=lambda e: roi_utils.cosine_similarity(e.emb, example.emb),
            reverse=False,  # from least to most
        )

        examples = []
        while len(ordered_examples) and k_tokens > 0:
            example = ordered_examples.pop()

            if example.n_tokens > k_tokens:
                break

            examples.append(example)
            k_tokens -= example.n_tokens

        # in prompt we want most similar examples to be first
        examples = list(reversed(examples))

        result = Prompt(system=self.system, examples=examples)
        assert len(ordered_examples) == 0 or result.n_tokens <= n_tokens

        return result

    def save(self, path=DEFAULT_PROMPT_FILE):
        data = {
            'system': self.system.messages,
            'examples': [
                {
                    'name': example.name,
                    'add_example_names': example.add_example_names,
                    'messages': example.messages,
                    'tasks': example.tasks,
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

        system = Example(cls.SYSTEM_NAME, messages=data['system'])
        examples = []
        for example_data in data['examples']:
            example = Example(
                name=example_data['name'],
                add_example_names=example_data['add_example_names'],
                messages=example_data['messages'],
                tasks=example_data['tasks'],
            )
            examples.append(example)

        return cls(system=system, examples=examples)

    def log(self, level=None, *, stdout=False, post_nl=False):
        assert level is not None or stdout
        examples_reprs = [repr(self.system)]
        for example in self.examples:
            examples_reprs.append(repr(example))

        full_repr = '\n'.join(examples_reprs) + '\n' * int(post_nl)
        if stdout:
            print(full_repr)
        else:
            logger.log(level, full_repr)
