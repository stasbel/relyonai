import os

import pandas as pd
import pytest

from aiknows import config

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# changing model chanes everything
config.model = 'gpt-3.5-turbo'


# * overall strategy
# - tests => fixing system/examples => fixing tests
# - we splits sync https calls for xdist to perform the best
# chat-gpt rate limit is 90k tokens per minute
# we want tests to be under 1 minute so say we got 90k tokens for single run
# each run is ~2k prompt + 0.3k-1k completition <= 3k
# so, 30 runs of `ai` :)

# * cases specification
# there could be several objectives for an `ai` call:
# - importing some module (module ..., import ..., etc.)
# - use arguments provided via kwargs
#   - we only encourage referecing arg via name, not implicitly
#   - plus minus minor mistakes and formatting is acceptable
# - lambdas ai('<imperative verb> ...)
#   - creating and reusing of the fly functions
#   - most sensible input spec should be assumed by description
#   - possible interleave with args
# - quick & easy gpt use right from code (summarize this, translate that, etc.)
# - all stuff related to file manipulations
# - inline chat-gpt code interpretator with any file
# - you forgot about something so you call ai


@pytest.fixture(scope='session')
def test_file_path():
    path = os.path.join(DATA_DIR, 'test.txt')
    assert os.path.exists(path)
    return path


@pytest.fixture
def cities_df():
    return pd.read_csv(os.path.join(DATA_DIR, 'cities.csv'))
