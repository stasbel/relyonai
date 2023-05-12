import os
import re

with open(os.path.join(os.path.dirname(__file__), '../pyproject.toml'), 'r') as f:
    PYTHON_VERSION = re.findall(r'requires-python\s*=\s*">=([\d.]+)"', f.read(), re.IGNORECASE)[0]

del os
del re

OPENAI_MODEL = 'gpt-3.5-turbo'
CACHE_DIR = '.askai.cache'

from .ai import ai  # noqa # pyright: ignore
from .gpt import gpt  # noqa # pyright: ignore
