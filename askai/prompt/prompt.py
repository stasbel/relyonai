import json
import os
from typing import Dict, List

import askai
from askai import explain

CURRENT_DIR = os.path.dirname(__file__)


def _get_system():
    with open(os.path.join(CURRENT_DIR, 'system.txt')) as f:
        return f.read().format(python_version=askai.PYTHON_VERSION)


def _get_examples():
    with open(os.path.join(CURRENT_DIR, 'examples.json')) as f:
        return json.load(f)


def make_query(task: str, **kwargs) -> str:
    args = ', '.join(kwargs.keys())
    explanations = '\n'.join(f'- {k}: """\n{explain.explain(v)}\n"""' for k, v in kwargs.items())
    return '''\
TASK: """
{task}
"""
ARGS: {args}
{explanations}
'''.format(
        task=task,
        args=args,
        explanations=explanations,
    ).strip(
        '\n'
    )


def make_prompt_messages(task: str, **kwargs) -> List[Dict[str, str]]:
    messages = []

    messages.append(
        {
            'role': 'system',
            'content': _get_system(),
        }
    )

    examples = _get_examples()
    for e in examples:
        messages.append(
            {
                'role': 'user',
                'content': e['query'],
            }
        )
        messages.append(
            {
                'role': 'assistant',
                'content': e['response'],
            }
        )

    messages.append(
        {
            'role': 'user',
            'content': make_query(task, **kwargs),
        }
    )

    return messages
