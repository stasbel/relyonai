import importlib

import numpy as np


def package_exists(package_name):
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
