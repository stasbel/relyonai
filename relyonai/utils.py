import importlib
import inspect
import os
import sys

import numpy as np

from relyonai import config


def package_exists(package_name):
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False


def python_intepreter_repr() -> str:
    result = [f'- version: {config.python_version}']

    result.append('- installed pip packages:')
    # distributions, _ = pip_chill.chill()
    # for p in distributions:
    #     result.append(f'    - {p.name}')
    result.append('   - numpy')
    result.append('   - pandas')

    return '\n'.join(result)


def is_inside_jupyter():
    return 'ipykernel' in sys.modules


def get_above_caller_file_path():
    # get the frame of the caller function
    frame = inspect.currentframe().f_back.f_back

    # get the file path of the caller frame
    file_path = inspect.getframeinfo(frame).filename

    return os.path.abspath(file_path)


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
