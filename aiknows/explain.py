from typing import Any

from aiknows import utils as ak_utils


def type_repr(x):
    module, class_name = type(x).__module__, type(x).__name__
    if module == 'builtins':
        return class_name
    else:
        return f'{module}.{class_name}'


def explain(x: Any) -> str:
    # TODO: x could be package or path or ... anything
    result = [f'type: {type_repr(x)}']

    if ak_utils.package_exists('numpy'):
        import numpy as np

        if isinstance(x, np.ndarray):
            # # too verbose, contain ptr and byteorder
            # buf = io.StringIO()
            # np.info(x, output=buf)
            # result.append(buf.getvalue())

            # simpler version
            result.append(f'shape: {x.shape}\ndtype: {x.dtype}')

    if ak_utils.package_exists('pandas'):
        import pandas as pd  # # pyright: ignore

        if isinstance(x, (pd.DataFrame, pd.Series)):
            # buf = io.StringIO()
            # x.info(buf=buf)
            # # skip type info on the first line
            # _, *info = buf.getvalue().split('\n')
            # result.extend(info)

            # simpler version
            result.append(
                f'shape: {x.shape}\n'
                f'columns: {x.columns.to_list()}\n'
                f'dtypes: {[t.name for t in x.dtypes.to_list()]}'
            )

    # merge lines
    result = '\n'.join(result).strip()

    return result
