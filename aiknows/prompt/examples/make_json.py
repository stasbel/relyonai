import contextlib
import glob
import logging

import nbformat

from aiknows import prompt
from aiknows.exceptions import AIKnowsTaskError

logger = logging.getLogger(__name__)

N_FIRST_TECHNICAL_CELLS = 2
N_LAST_TECHNICAL_CELLS = 1
NBS_ORDER = (
    'package',
    'const',
    'error_fixing',
    'sum_xy',
    'sum_x',
    'sum_y',
    'sum',
    'file_arg',
    'file_noarg',
    'plt',
    'gpt',
    'task_error',
    'task_error_cause',
)


class ExampleNotebookRuntime:
    def __init__(self, notebook_path):
        super().__init__()

        with open(notebook_path) as f:
            self.nb = nbformat.read(f, as_version=4)

        self.pos = 0
        self.globals = {}

    def __len__(self):
        return len(self.nb.cells)

    @property
    def steps_left(self):
        return len(self) - self.pos

    def next_cell_code(self):
        cell = self.nb.cells[self.pos]
        assert cell.cell_type == 'code'

        code = cell.source.strip()
        # if code sell is what we expect to predict (last cell could be an error)
        if N_FIRST_TECHNICAL_CELLS <= self.pos < len(self) - N_LAST_TECHNICAL_CELLS:
            *code, last_line = code.split('\n')
            last_line = last_line.strip()

            if self.steps_left != N_LAST_TECHNICAL_CELLS + 1:  # all but last
                assert last_line in ('result', 'final_result')
                code = '\n'.join(code)
            else:  # last
                if last_line == 'final_result':
                    code = '\n'.join(code)
                else:
                    code = '\n'.join(code + [last_line])

        return code

    def run_next_cell(self):
        code = self.next_cell_code()
        self.pos += 1

        with contextlib.redirect_stdout(None):  # don't care about stdout in examples
            exec(code, self.globals)


def collect_messages(chat, runtime):
    # first two cells are task/args and globals setup
    runtime.run_next_cell()
    task, args = runtime.globals['TASK'], runtime.globals['ARGS']
    runtime.run_next_cell()  # here we remove task/args from globals

    chat.add_user_task(task, **args)

    for _ in range(len(runtime) - N_FIRST_TECHNICAL_CELLS - N_LAST_TECHNICAL_CELLS):
        code = runtime.next_cell_code()
        chat.add_assistant(code)

        try:
            runtime.run_next_cell()
        except Exception as e:
            if isinstance(e, AIKnowsTaskError):
                # should be last cell -- assistant tell to stop process explicitly
                assert runtime.steps_left == N_LAST_TECHNICAL_CELLS

                continue

            # it's a bad example if last cell ending in error
            assert runtime.steps_left != N_LAST_TECHNICAL_CELLS

            chat.add_user_error(e)
        else:
            # if code cell is last => exit loop
            if runtime.steps_left == N_LAST_TECHNICAL_CELLS:
                # loosely checking that we have have correct example
                assert 'final_result' in runtime.globals

                continue

            chat.add_user_result(runtime.globals['result'])

    # last cell is final result check
    runtime.run_next_cell()
    assert runtime.steps_left == 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    nbs_paths_order = [f'{nb_name}.ipynb' for nb_name in NBS_ORDER]
    # minus template.ipynb
    assert set(nbs_paths_order) == set(glob.glob('*.ipynb')) - {'template.ipynb'}

    chat = prompt.Chat()
    for nb_path in nbs_paths_order:
        runtime = ExampleNotebookRuntime(nb_path)
        collect_messages(chat, runtime)

    for m in chat.messages:
        logger.info('role: %s message:\n%s', m['role'], m['content'])

    chat.save('examples')
    logger.info('saved to examples.json')
