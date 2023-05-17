import logging

import nbformat

from aiknows import prompt as ak_prompt
from aiknows import runtime as ak_runtime

logger = logging.getLogger(__name__)


NBS_ORDER = (
    'modules',
    'const',
    'sums',
    'files',
    'plt',
    'gpt',
    'error_fixing',
    'task_errors',
    'lambdas',
    'exploration',
    'reuse',
    # 'template',
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


def collect_messages(chat, runtime, nb_path):
    nb_parser = ExampleNotebookParser(nb_path)

    active_task = False
    for _ in range(len(nb_parser)):
        code = nb_parser.next_cell_code()

        try:
            # don't care about stdout in examples
            result = runtime.run(code, supress_stdout=True)
        except ak_runtime.SetupTaskSignal as e:
            assert not active_task
            chat.add_user_task(e.task, e.reuse, **e.args)
            if not e.reuse:
                runtime.clear()
                runtime.add_vars(e.args)
            active_task = True
            continue
        except Exception as e:
            assert active_task
            chat.add_assistant(code)

            if isinstance(e, (ak_runtime.FinishTaskOKSignal, ak_runtime.FinishTaskErrorSignal)):
                active_task = False
                continue

            chat.add_user_error(e)
        else:
            assert active_task
            chat.add_assistant(code)
            chat.add_user_result(result)

    assert not active_task


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    nbs_paths_order = [f'{nb_name}.ipynb' for nb_name in NBS_ORDER]
    # minus template.ipynb
    # assert set(nbs_paths_order) == set(glob.glob('*.ipynb')) - {'template.ipynb'}

    chat, runtime = ak_prompt.Chat(add_example_names=True), ak_runtime.LocalRuntime()
    for nb_path in nbs_paths_order:
        collect_messages(chat, runtime, nb_path)

    chat.log_all_messages(logging.INFO)

    chat.save('examples/examples.json')
    logger.info('saved to examples.json')
