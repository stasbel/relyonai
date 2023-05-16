import logging

import nbformat

from aiknows import prompt, runtime

logger = logging.getLogger(__name__)


NBS_ORDER = (
    'package',
    'const',
    'error_fixing',
    # 'sum_xy',
    # 'sum_x',
    # 'sum_y',
    # 'sum',
    'file_arg',
    'file_noarg',
    'file_const',
    'plt',
    'gpt',
    'task_error',
    'task_error_cause',
    'function',
    'exploration',
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


def collect_messages(chat, nb_path):
    nb_parser = ExampleNotebookParser(nb_path)
    local_runtime = runtime.LocalRuntime()

    active_task = False
    for _ in range(len(nb_parser)):
        code = nb_parser.next_cell_code()

        try:
            # don't care about stdout in examples
            result = local_runtime.run(code, supress_stdout=True)
        except runtime.SetupTaskSignal as e:
            assert not active_task
            chat.add_user_task(e.task, e.reuse, **e.args)
            if not e.reuse:
                local_runtime.clear()
                local_runtime.add_vars(e.args)
            active_task = True
            continue
        except Exception as e:
            assert active_task
            chat.add_assistant(code)

            if isinstance(e, (runtime.FinishTaskOKSignal, runtime.FinishTaskErrorSignal)):
                active_task = False
                continue

            chat.add_user_error(e)
        else:
            assert active_task
            chat.add_assistant(code)
            chat.add_user_result(result)
            local_runtime.add_vars({'_': result})

    assert not active_task


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    nbs_paths_order = [f'{nb_name}.ipynb' for nb_name in NBS_ORDER]
    # minus template.ipynb
    # assert set(nbs_paths_order) == set(glob.glob('*.ipynb')) - {'template.ipynb'}

    runtime.throw_signals = True
    chat = prompt.Chat()
    for nb_path in nbs_paths_order:
        collect_messages(chat, nb_path)

    for m in chat.messages:
        logger.info('role: %s message:\n%s', m['role'], m['content'])

    chat.save('examples')
    logger.info('saved to examples.json')
