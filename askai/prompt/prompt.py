import json
import logging
import os
import traceback

import askai
from askai import explain

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(__file__)


class Chat:
    # refer to SCHEMA.md for the format

    def __init__(self, messages=None):
        super().__init__()

        self.messages = messages or []

    def add_system(self):
        with open(os.path.join(CURRENT_DIR, 'system.txt')) as f:
            content = f.read().format(python_version=askai.PYTHON_VERSION)

        self.messages.append(
            {
                'role': 'system',
                'content': content,
            }
        )

    def add_user_task(self, task, **kwargs):
        schema = 'TASK: """\n{task}\n"""\nARGS: {args_list}\n{args_explanations}'
        args_list_repr = ', '.join(kwargs.keys())
        args_explanations = []
        for k, v in kwargs.items():
            v_explanation = explain.explain(v)
            if len(v_explanation) > askai.TRUNCATE_REPR:
                logger.warning('truncating explanation to %d chars', askai.TRUNCATE_REPR)
                v_explanation = v_explanation[: askai.TRUNCATE_REPR] + '...[truncated]'

            args_explanations.append(f'- {k}: """\n{v_explanation}\n"""')

        content = schema.format(
            task=task,
            args_list=args_list_repr,
            args_explanations='\n'.join(args_explanations),
        ).strip()

        self.messages.append(
            {
                'role': 'user',
                'content': content,
            }
        )

    def add_user_result(self, result):
        result_repr = repr(result)
        if len(result_repr) > askai.TRUNCATE_REPR:
            logger.warning('truncating result repr to %d chars', askai.TRUNCATE_REPR)
            result_repr = result_repr[: askai.TRUNCATE_REPR] + '...[truncated]'

        self.messages.append({'role': 'user', 'content': f'RESULT: """\n{result_repr}\n"""'})

    def add_user_error(self, error):
        tb = traceback.extract_tb(error.__traceback__)
        last_frame_repr = ''.join(traceback.format_list([tb[-1]])).strip()
        traceback_repr = ''.join(traceback.format_exception_only(type(error), error)).strip()
        error_repr = f'{last_frame_repr}\n{traceback_repr}'

        if len(error_repr) > askai.TRUNCATE_REPR:
            logger.warning('truncating error repr to %d chars', askai.TRUNCATE_REPR)
            error_repr = error_repr[: askai.TRUNCATE_REPR] + '...[truncated]'

        self.messages.append({'role': 'user', 'content': f'ERROR: """\n{error_repr}\n"""'})

    def add_assistant(self, code):
        self.messages.append({'role': 'assistant', 'content': f'```python\n{code}\n```'})

    def save(self, name):
        with open(os.path.join(CURRENT_DIR, f'examples/{name}.json'), 'w') as f:
            json.dump(self.messages, f)

    def load(self, name):
        with open(os.path.join(CURRENT_DIR, f'examples/{name}.json'), 'r') as f:
            self.messages.extend(json.load(f))
