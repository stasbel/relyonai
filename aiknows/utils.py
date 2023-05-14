import importlib


def package_exists(package_name):
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False
