import io
from typing import Any

from aiknows import utils


def _type_repr(x):
    return f"{type(x).__module__}.{type(x).__name__}"


def explain(x: Any) -> str:
    # TODO: x could be package or path or ... anything
    result = [f'object of type {_type_repr(x)}']

    if utils.package_exists('numpy'):
        import numpy as np

        if isinstance(x, np.ndarray):
            # # too verbose, contain ptr and byteorder
            # buf = io.StringIO()
            # np.info(x, output=buf)
            # result.append(buf.getvalue())

            # simpler version
            result.append(f'array of shape {x.shape} with dtype {x.dtype}')

    if utils.package_exists('pandas'):
        import pandas as pd  # # pyright: ignore

        if isinstance(x, (pd.DataFrame, pd.Series)):
            buf = io.StringIO()
            x.info(buf=buf)
            # skip type info on the first line
            _, *info = buf.getvalue().split('\n')
            result.extend(info)

    # merge lines
    result = '\n'.join(result).strip()

    return result
