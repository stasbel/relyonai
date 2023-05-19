import functools
import os
import sys

import pandas as pd
import pytest

from aiknows import ai, config

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# chat-gpt rate limit is 90k tokens per minute
# we want tests to be under 1 minute so say we got 90k tokens for single run
# each run is ~2k prompt + 0.3k-1k completition <= 3k
# so, 30 runs of `ai` :)
config.model = 'gpt-3.5-turbo'

# ! important note
# to be hosent, gpt-3.5 is too dumb to understand when to use args and when to creat a func
# I mean you could get it to work on some cases, but there it's not a robust solution

# * overall strategy
# - tests => fixing system/examples => fixing tests
# - we splits sync https calls for xdist to perform the best

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


@pytest.fixture
def file_path():
    return os.path.join(CURRENT_DIR, 'test.txt')


@pytest.fixture
def cities_df():
    return pd.read_csv(os.path.join(CURRENT_DIR, 'cities.csv'))


def test_modules():
    assert ai('standard module for handy higher-order functions') is functools
    assert ai('import system stuff module') is sys


def test_const():
    assert ai('number of toes on a human feet') == 10


def test_sum():
    assert ai('sum of 1 and 1') == 2
    assert ai('sum of 1 and x', x=10) == 11


def test_translation():
    assert 'bonjour' in ai('translate s to french', s='hello').lower()


def test_reasoning():
    assert ai('return answer key from d', d={'Q': 'bark', 'A': 'dog'}) == 'dog'


def test_lambdas_1():
    list_x = [2, 3, 4, 5, 6, 7, 8, 9]
    assert ai('a list of non primes in list_x', list_x=list_x) == [4, 6, 8, 9]


def test_lambdas_2():
    assert ai('filter non primes out')([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == [2, 3, 5, 7]


def test_lambdas_3():
    f = ai('filter palindromes away')
    assert f(['hello', 'world', 'racecar', 'foo', 'bar']) == ['hello', 'world', 'foo', 'bar']
    assert f(['abc', 'ccc']) == ['abc']


def test_lambdas_4():
    assert ai('merge two lists into dict')([1, 2, 3], ['a', 'b', 'c']) == {1: 'a', 2: 'b', 3: 'c'}


def test_lambdas_5():
    assert ai('unique elements in a - b', a=set([1, 2, 3, 4, 5]), b=set([1, 2, 3])) == {4, 5}


def test_lambdas_6():
    assert len(ai('filter out every third element')(list(range(900)))) == 600


def test_files_1(file_path):
    assert os.path.exists(file_path)
    assert ai('a function that reads file')(file_path) == 'content'
    assert ai('read file at filepath', filepath=file_path) == 'content'


def test_files_2(file_path):
    assert os.path.exists(file_path)
    assert ai('count number of letter "t" occurence inside file', file=file_path) == 2


def test_session():
    r, sess = ai('sum numbers in x', x=[1, 2, 3, 4, 5], save_session=True)
    assert r == 15
    assert sess.ai('multiply numbers in x') == 120


def test_list_reverse():
    assert ai('reverse a list')(list(range(10))) == list(range(9, -1, -1))


def test_regexps():
    check_number = ai('check if input is a valid US phone number starts with +1')
    assert check_number('+12345678900')
    assert not check_number('not a number')
    check_http = ai('check if input is a valid http url')
    assert check_http('http://google.com')
    assert not check_http('not an url')


def test_extractor():
    extractor = ai('extract all 000-000-0000 format phone numbers from text')
    assert extractor('my phone number is 123-456-7890') == ['123-456-7890']


def test_dataframes(cities_df):
    # someties it's ok, most of the times fail
    _, sess = ai('return the two most distant cities in df', df=cities_df, save_session=True)
    r = sess.ai('strip all unnecessary symbols like spaces and \'\" from previous result')
    assert set(r) == {'West Palm Beach', 'Vancouver'}


def test_format():
    formatter = ai('format a float to have 2 digits after .')
    assert formatter(3.1415926) == '3.14'
    assert formatter(3.149) == '3.15'
    assert formatter(3.1) == '3.10'
    assert formatter(3) == '3.00'
    assert formatter(3.99) == '3.99'
    assert formatter(3.50000000) == '3.50'


def test_generators():
    def stream():
        for i in range(1000):
            yield i

    f = ai('leave only even numbers in an input generator')
    assert len(list(f(stream()))) == 500
    g = ai('leave numbers at even positions in an input generator')
    assert len(list(g(stream()))) == 500
    assert len(list(g(f(stream())))) == 250
    assert len(list(f(g(stream())))) == 500


def test_http():
    url = 'https://api.coindesk.com/v1/bpi/currentprice/BTC.json'
    r = ai('get a jsom data from url', url=url)
    assert r['bpi']['USD']['code'] == 'USD'
