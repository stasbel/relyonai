import ast
import contextlib
import traceback
from typing import Any, Callable, Dict, Optional, Union

from aiknows import gpt


class ControlFlowSignal(Exception):
    pass


class SetupTaskSignal(ControlFlowSignal):
    """Exception raised by assistant when task is begining."""

    def __init__(self, task: str, env: str, args: Dict[str, Any]) -> None:
        super().__init__()

        self.task = task
        self.env = env
        self._args = args

    @property
    def args(self) -> Dict[str, Any]:
        return self._args

    def __repr__(self) -> str:
        return '{class_name}(task={task}, env={env}, args={args})'.format(
            class_name=self.__class__.__name__,
            task=repr(self.task),
            env=repr(self.env),
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

    def __init__(self, message: str, error_cause: Union[bool, Exception] = False) -> None:
        super().__init__()

        self.message = message
        self.error_cause = error_cause

    def __repr__(self) -> str:
        return '{class_name}(message={message}, error_cause={error_cause})'.format(
            class_name=self.__class__.__name__,
            message=repr(self.message),
            error_cause=repr(self.error_cause),
        )


_can_throw_signals = False
_last_validator = None
_last_result = None


@contextlib.contextmanager
def enable_signals() -> None:
    global _can_throw_signals
    assert not _can_throw_signals
    _can_throw_signals = True
    try:
        yield
    finally:
        _can_throw_signals = False


def setup_task(
    *,
    task: str,
    env: bool = 'new',
    args: Optional[Dict[str, Any]] = None,
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

    # print assistant's prompt (user/task)
    from aiknows import prompt as ak_prompt

    example = ak_prompt.Example()
    args = args or {}
    example.add_user_task(task, env, args)
    example.log(stdout=True)

    # construct context
    if env == 'new':
        # when we executing inside jupyter this is unset
        # because we can't clear globals in jupyter -- this would break stuff
        if _can_throw_signals:
            globals.clear()

        clean_runtime = LocalRuntime()
        clean_runtime.add_vars(args)
        globals.update(clean_runtime.globals)

    if env == 'same':
        globals.update({'_': _last_result})

    # save validator for later finishing
    global _last_validator
    _last_validator = validator

    # only raise exception in real runtime
    if _can_throw_signals:
        raise SetupTaskSignal(task, env, args)


def finish_task_ok(result: Any = None, message: Optional[str] = None) -> None:
    global _last_result
    _last_result = result

    if _last_validator is not None:
        assert _last_validator(result)

    if _can_throw_signals:
        raise FinishTaskOKSignal(result, message)


def finish_task_error(message: str, error_cause: Union[bool, Exception] = False) -> None:
    if _can_throw_signals:
        raise FinishTaskErrorSignal(message, error_cause)


class RuntimeError(Exception):
    pass


class HistroyLimitError(RuntimeError):
    pass


class ResponseFormatError(RuntimeError):
    pass


class InvalidTaskError(RuntimeError):
    pass


class LocalRuntime:
    EXEC_BODY_FILENAME = '<assistant>'
    EXEC_LAST_FILENAME = '<assistant>'
    RESERVED_GLOBALS = {
        'gpt': gpt,
        'finish_task_ok': finish_task_ok,
        'finish_task_error': finish_task_error,
    }

    def __init__(self, *, source_file_path=None) -> None:
        super().__init__()

        self.source_file_path = source_file_path

        self.globals = {}
        self.clear()

    def _execute_jupyter_style(self, code):
        """jupyter style == return last expression value or None if has ;"""

        # https://docs.python.org/3/library/functions.html#compile
        # https://docs.python.org/3/library/functions.html#exec
        # * bytecode isn't pickable by joblib (though we can parse ast first)
        # bytecode = compile(code, '<gpt>', 'exec')

        # code = code.strip()

        # Parse the code into an AST
        tree = ast.parse(code)

        # Get the last body element
        last = tree.body[-1]

        # Check if the last body element ends with semicolon
        last_line = code.split('\n')[-1]
        return_last_expr = not last_line.rstrip().endswith(';')

        # Remove the last body element from the original tree
        tree.body = tree.body[:-1]

        exec(compile(tree, filename=self.EXEC_BODY_FILENAME, mode='exec'), self.globals)

        if return_last_expr and isinstance(last, ast.Expr):
            # If the last body element does not end with semicolon, return its value
            last = ast.Expression(last.value)
            return eval(compile(last, filename=self.EXEC_LAST_FILENAME, mode='eval'), self.globals)
        else:
            # If the last body element ends with semicolon, do not return its value
            last = ast.Module(body=[last], type_ignores=[])
            exec(compile(last, filename=self.EXEC_LAST_FILENAME, mode='exec'), self.globals)
            return None

    @staticmethod
    def error_repr(error, *, at_parsing=False, at_runtime=False, code=None):
        result = []

        if at_parsing:
            pass

        if at_runtime:
            last_tb = traceback.extract_tb(error.__traceback__)[-1]
            last_frame_repr = ''.join(traceback.format_list([last_tb])).strip()
            result.append(last_frame_repr)

            source_code_repr = '  ' + code.split('\n')[last_tb.lineno - 1].strip()
            result.append(source_code_repr)

        traceback_repr = ''.join(traceback.format_exception_only(type(error), error)).strip()
        result.append(traceback_repr)

        return '\n'.join(result)

    def run(self, code: str, *, supress_stdout: bool = False) -> Any:
        with contextlib.redirect_stdout(None) if supress_stdout else contextlib.nullcontext():
            with enable_signals():
                result = self._execute_jupyter_style(code)

        self.add_vars({'_': result})
        return result

    def add_vars(self, args: Dict[str, Any]) -> None:
        self.globals.update(args)

    def clear(self) -> None:
        self.globals.clear()
        if self.source_file_path is not None:
            self.add_vars({'__file__': self.source_file_path})
        self.add_vars(self.RESERVED_GLOBALS)
