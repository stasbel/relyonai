import ast
import contextlib
from typing import Any, Callable, Dict, Optional

from aiknows import gpt, prompt


class ControlFlowSignal(Exception):
    pass


class SetupTaskSignal(ControlFlowSignal):
    """Exception raised by assistant when task is begining."""

    def __init__(self, task: str, reuse: bool, args: Dict[str, Any]) -> None:
        super().__init__()

        self.task = task
        self.reuse = reuse
        self._args = args

    @property
    def args(self) -> Dict[str, Any]:
        return self._args

    def __repr__(self) -> str:
        return '{class_name}(task={task}, reuse={reuse}, args={args})'.format(
            class_name=self.__class__.__name__,
            task=repr(self.task),
            reuse=repr(self.reuse),
            args=repr(self.args),
        )


class FinishTaskOKSignal(ControlFlowSignal):
    """Exception raised by assistant when task is complete."""

    def __init__(self, result: Any, message: Optional[str] = None) -> None:
        super().__init__()

        self.result = result
        self.message = message

    def __repr__(self) -> str:
        return '{class_name}(result={result}, message={message})'.format(
            class_name=self.__class__.__name__,
            result=repr(self.result),
            message=repr(self.message),
        )


class FinishTaskErrorSignal(ControlFlowSignal):
    """Exception raised by assistant when task can't be complete."""

    def __init__(self, message: str, error_cause: bool = False) -> None:
        super().__init__()

        self.message = message
        self.error_cause = error_cause

    def __repr__(self) -> str:
        return '{class_name}(message={message}, error_cause={error_cause})'.format(
            class_name=self.__class__.__name__,
            message=repr(self.message),
            error_cause=repr(self.error_cause),
        )


throw_signals = False
_last_validator = None


def setup_task(
    *,
    task: str,
    reuse: bool,
    args: Optional[Dict[str, Any]],
    globals: Dict[str, Any],
    validator: Optional[Callable[[Any], bool]] = None,
) -> None:
    """setups global context for task

    that way, we fix up the global context:
    1) introduce args for reference in actual code (consistent with py runtime)
    2) delete all unnecessary variables to remove pollution
    3) jupyter global vars (like d above) still allow for easier coding
    there are still number of globals left (introduced by the jupyter)
    however, let's not overengineer stuff and forget about them 😀

    """

    # new args can shadow common, but rn we don't allow this
    args = args or {}
    assert len(set(LocalRuntime.RESERVED_GLOBALS.keys()) & set(args.keys())) == 0

    # print assistant's prompt (user/task)
    chat = prompt.Chat()
    chat.add_user_task(task, reuse, **args)
    print(chat.messages[-1]['content'])

    # construct context
    if not reuse:
        # we can't clean globals in jupyter
        if throw_signals:
            globals.clear()
        clean_local_runtime = LocalRuntime()
        clean_local_runtime.add_vars(args)
        globals.update(clean_local_runtime.globals)

    # save validator for later finishing
    global _last_validator
    _last_validator = validator

    # only raise exception in real runtime
    if throw_signals:
        raise SetupTaskSignal(task, reuse, args)


def finish_task_ok(result: Any, message: Optional[str] = None) -> None:
    if _last_validator is not None:
        assert _last_validator(result)

    if throw_signals:
        raise FinishTaskOKSignal(result, message)


def finish_task_error(message: str, error_cause: bool = False) -> None:
    if throw_signals:
        raise FinishTaskErrorSignal(message, error_cause)


class LocalRuntime:
    EXEC_FILENAME = '<gpt>'
    RESERVED_GLOBALS = {
        'gpt': gpt,
        'finish_task_ok': finish_task_ok,
        'finish_task_error': finish_task_error,
    }

    def __init__(self) -> None:
        super().__init__()

        self.globals = {}

        self.clear()

    def _execute_jupyter_style(self, code):
        """jupyter style == return last expression value or None if has ;"""

        # print('code:', code)

        code = code.strip()

        # Parse the code into an AST
        tree = ast.parse(code)

        # Get the last body element
        last = tree.body[-1]

        # Check if the last body element ends with semicolon
        last_line = code.split('\n')[-1]
        return_last_expr = not last_line.rstrip().endswith(';')

        # Remove the last body element from the original tree
        tree.body = tree.body[:-1]

        exec(compile(tree, filename=self.EXEC_FILENAME, mode='exec'), self.globals)

        if return_last_expr and isinstance(last, ast.Expr):
            # If the last body element does not end with semicolon, return its value
            last = ast.Expression(last.value)
            return eval(compile(last, filename=self.EXEC_FILENAME, mode='eval'), self.globals)
        else:
            # If the last body element ends with semicolon, do not return its value
            last = ast.Module(body=[last], type_ignores=[])
            exec(compile(last, filename=self.EXEC_FILENAME, mode='exec'), self.globals)
            return None

    def run(self, code: str, *, supress_stdout: bool = False) -> Any:
        with contextlib.redirect_stdout(None) if supress_stdout else contextlib.nullcontext():
            return self._execute_jupyter_style(code)

    def add_vars(self, args: Dict[str, Any]) -> None:
        self.globals.update(args)

    def clear(self) -> None:
        self.globals.clear()
        self.globals.update(self.RESERVED_GLOBALS)
