import os
import re
from dataclasses import dataclass
from typing import Any

with open(os.path.join(os.path.dirname(__file__), '../pyproject.toml'), 'r') as f:
    PYTHON_VERSION = re.findall(r'requires-python\s*=\s*">=([\d.]+)"', f.read(), re.IGNORECASE)[0]

AVAILABLE_MODELS = ('gpt-3.5-turbo', 'gpt-4')
MODELS_PRICING_DOLLARS_PER_1K_PROMPT_TOKENS = {
    'gpt-3.5-turbo': 0.002,
    'gpt-4': 0.03,
}
MODELS_PRICING_DOLLARS_PER_1K_COMPLETITION_TOKENS = {
    'gpt-3.5-turbo': 0.002,
    'gpt-4': 0.06,
}

# cache is stored in main package directory
CACHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '.aiknows.cache'))


@dataclass
class _Config:
    python_version: str = PYTHON_VERSION
    model: str = 'gpt-3.5-turbo'
    n_truncate_repr: int = 150
    history_len_max: int = 5
    cache_path: str = CACHE_PATH

    # more like a common private var
    _session_n_prompt_tokens: int = 0
    _session_n_completition_tokens: int = 0

    def __init__(self) -> None:
        super().__init__()

    def __setattr__(self, key: str, value: Any) -> None:
        if key == 'model':
            if value not in AVAILABLE_MODELS:
                raise ValueError(f'invalid model {value}, must be one of {AVAILABLE_MODELS}')

        return super().__setattr__(key, value)

    def update_session_tokens(self, response) -> None:
        self._session_n_prompt_tokens += response['usage']['prompt_tokens']
        self._session_n_completition_tokens += response['usage']['completion_tokens']

    @property
    def session_dollars_spend(self) -> float:
        prompt_money = MODELS_PRICING_DOLLARS_PER_1K_PROMPT_TOKENS[self.model] * (
            self._session_n_prompt_tokens / 1000
        )
        completition_money = MODELS_PRICING_DOLLARS_PER_1K_COMPLETITION_TOKENS[self.model] * (
            self._session_n_completition_tokens / 1000
        )
        return prompt_money + completition_money


# not thread/process safe :(
config = _Config()
