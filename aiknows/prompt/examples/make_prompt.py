import logging
import os

import nbformat

from aiknows import prompt as ak_prompt
from aiknows import runtime as ak_runtime

logger = logging.getLogger(__name__)


NBS_ORDER = (
    # 'template',
    'imports',
    'consts',
    'files',
    'funcs1',
    'funcs2',
    'funcs3',
    'gpt',
    'session',
    'errors',
    # 'sums',
    # 'plt',
    # 'error_fixing',
    # 'task_errors',
    # 'lambdas',
    # 'exploration',
    # 'env',
)


class ExampleNotebookParser:
    def __init__(self, notebook_path):
        super().__init__()

        with open(notebook_path) as f:
            self.nb = nbformat.read(f, as_version=4)

        self.pos = 0

    def __len__(self):
        return len(self.nb.cells)

    def next_cell_code(self):
        cell = self.nb.cells[self.pos]
        assert cell.cell_type == 'code'
        code = cell.source.strip()
        self.pos += 1
        return code


def make_format_example(runtime):
    nb_parser = ExampleNotebookParser('format.ipynb')
    example = ak_prompt.Example('format')

    # setup
    code = nb_parser.next_cell_code()
    try:
        runtime.run(code, supress_stdout=True)
    except ak_runtime.SetupTaskSignal as e:
        example.add_user_task(e.task, e.env, e.args)
        runtime.clear()
        runtime.add_vars(e.args)

    # code error
    code = nb_parser.next_cell_code()
    dirty_code = '```python\n' + code
    example.add_assistant(dirty_code)
    try:
        example.strip_code_markdown(dirty_code)
    except Exception as e:
        example.add_user_error(e)

    # code correct
    try:
        runtime.run(code, supress_stdout=True)
    except ak_runtime.FinishTaskOKSignal:
        example.add_assistant(code, add_markdown=True)

    return example


def make_example(runtime, nb_path):
    nb_parser = ExampleNotebookParser(nb_path)
    name = os.path.splitext(os.path.basename(nb_path))[0]
    example = ak_prompt.Example(name)

    active_task = False
    for _ in range(len(nb_parser)):
        code = nb_parser.next_cell_code()

        try:
            # don't care about stdout in examples
            result = runtime.run(code, supress_stdout=True)
        except ak_runtime.SetupTaskSignal as e:
            assert not active_task
            example.add_user_task(e.task, e.env, e.args)
            if e.env == 'new':
                runtime.clear()
                runtime.add_vars(e.args)
            active_task = True
            continue
        except Exception as e:
            assert active_task
            example.add_assistant(code, add_markdown=True)

            if isinstance(e, (ak_runtime.FinishTaskOKSignal, ak_runtime.FinishTaskErrorSignal)):
                active_task = False
                continue

            example.add_user_error(e, at_runtime=True, code=code)
        else:
            assert active_task
            example.add_assistant(code, add_markdown=True)
            example.add_user_result(result)

    assert not active_task

    return example


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    nbs_paths_order = [f'{nb_name}.ipynb' for nb_name in NBS_ORDER]
    # minus template.ipynb
    # assert set(nbs_paths_order) == set(glob.glob('*.ipynb')) - {'template.ipynb'}

    system = ak_prompt.Prompt.load_system('simpler2.md')
    prompt, runtime = ak_prompt.Prompt(system), ak_runtime.LocalRuntime()

    # format_example = make_format_example(runtime)
    # prompt.add_example(format_example)
    # logger.info('example %s added: %d tokens', format_example.name, format_example.n_tokens)

    for nb_path in nbs_paths_order:
        example = make_example(runtime, nb_path)
        prompt.examples.append(example)
        logger.info('example %s added: %d tokens', example.name, example.n_tokens)

    # a little test
    test_example = ak_prompt.Example()
    test_example.add_user_task('import numpy', 'new', {})
    ordered_examples = prompt.fill_up_to_n_tokens(test_example, 2000)
    assert ordered_examples.examples[-1].name == 'imports'

    prompt.log(logging.INFO, post_nl=True)

    prompt.save()
    logger.info('prompt saved to file %s', ak_prompt.DEFAULT_PROMPT_FILE)
