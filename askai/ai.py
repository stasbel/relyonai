import logging
from typing import Any

from askai import prompt, utils

MODEL = 'gpt-3.5-turbo'


def ai(task: str, **kwargs) -> Any:
    import openai

    prompt_messages = prompt.make_prompt_messages(task, **kwargs)
    logging.info(f'len prompt messages: {len(prompt_messages)}')

    if utils.package_exists('tiktoken'):
        import tiktoken

        tokenizer = tiktoken.encoding_for_model(MODEL)
        prompt_len = len(tokenizer.encode('\n'.join(m['content'] for m in prompt_messages)))
        logging.info(f'prompt length: {prompt_len}')

    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=prompt_messages,
        temperature=0.0,
    )
    response = response['choices'][0]['message']['content'].strip()
    __code__ = response

    # delete stuff so it doesn't capture in exec
    del response
    del openai

    return __code__

    # exec(__code__)
    # return result
