import importlib
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

PYTHON_VERSION = f'{sys.version_info.major}.{sys.version_info.minor}'

AVAILABLE_MODELS = ('gpt-3.5-turbo', 'gpt-3.5-turbo-0301', 'gpt-4')
AVAILABLE_EMBEDDING_MODELS = 'text-embedding-ada-002'
MODELS_PRICING_DOLLARS_PER_1K_PROMPT_TOKENS = {
    'gpt-3.5-turbo': 0.002,
    'gpt-3.5-turbo-0301': 0.002,
    'gpt-4': 0.03,
}
MODELS_PRICING_DOLLARS_PER_1K_COMPLETITION_TOKENS = {
    'gpt-3.5-turbo': 0.002,
    'gpt-3.5-turbo-0301': 0.002,
    'gpt-4': 0.06,
}
EMBEDDING_MODELS_PRICING_DOLLARS_PER_1K_TOKENS = {
    'text-embedding-ada-002': 0.0004,
}

# cache is stored in ~~main package~~ home directory
# CACHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '.aiknows.cache'))
CACHE_PATH = os.path.expanduser('~/.cache/aiknows')


@dataclass
class _Config:
    python_version: str = PYTHON_VERSION
    model: str = 'gpt-3.5-turbo'
    embedding_model: str = 'text-embedding-ada-002'
    n_tokens_relevant_prompt: int = 2048  # half of chat-gpt maximum
    n_truncate_repr: int = 300
    history_len_max: int = 5
    cache_path: str = CACHE_PATH
    dollars_limit: float = 1.0

    # more like a common private var
    _n_prompt_tokens: int = 0
    _n_completition_tokens: int = 0
    _n_embedding_tokens: int = 0

    def __init__(self) -> None:
        super().__init__()

    def __setattr__(self, key: str, value: Any) -> None:
        if key == 'model':
            if value not in AVAILABLE_MODELS:
                raise ValueError(f'invalid model {value}, must be one of {AVAILABLE_MODELS}')

        if key == 'embedding_model':
            if value not in AVAILABLE_EMBEDDING_MODELS:
                raise ValueError(
                    f'invalid embedding model {value},'
                    f'must be one of {AVAILABLE_EMBEDDING_MODELS}'
                )

        if key == 'cache_path':
            from aiknows import llm as ak_llm

            importlib.reload(ak_llm)

        return super().__setattr__(key, value)

    def clear_cache(self) -> None:
        if os.path.exists(self.cache_path) and os.path.isdir(self.cache_path):
            shutil.rmtree(self.cache_path)

    def cache_size_mb(self) -> float:
        result = subprocess.run(['du', '-sh', self.cache_path], capture_output=True, text=True)
        return float(result.stdout.split('\t')[0][:-1])

    def update_tokens(self, response) -> None:
        self._n_prompt_tokens += response['usage'].get('prompt_tokens', 0)
        self._n_completition_tokens += response['usage'].get('completion_tokens', 0)

    def update_embedding_tokens(self, response) -> None:
        self._n_embedding_tokens += response['usage'].get('prompt_tokens', 0)

    @property
    def dollars_spent(self) -> float:
        prompt_money = MODELS_PRICING_DOLLARS_PER_1K_PROMPT_TOKENS[self.model] * (
            self._n_prompt_tokens / 1000
        )
        completition_money = MODELS_PRICING_DOLLARS_PER_1K_COMPLETITION_TOKENS[self.model] * (
            self._n_completition_tokens / 1000
        )
        embedding_money = EMBEDDING_MODELS_PRICING_DOLLARS_PER_1K_TOKENS[self.embedding_model] * (
            self._n_embedding_tokens / 1000
        )
        return prompt_money + completition_money + embedding_money


# not thread/process safe :( 😭
config = _Config()
