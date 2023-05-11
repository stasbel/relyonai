import os
import re

from .ai import ai  # noqa # pyright: ignore

with open(os.path.join(os.path.dirname(__file__), '../pyproject.toml'), 'r') as f:
    PYTHON_VERSION = re.findall(r'requires-python\s*=\s*">=([\d.]+)"', f.read(), re.IGNORECASE)[0]

del os
del re
