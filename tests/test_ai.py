import functools
import os

import pandas as pd
import pytest

from aiknows import ai

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def file_path():
    return os.path.join(CURRENT_DIR, 'test.txt')


@pytest.fixture
def cities_df():
    return pd.read_csv(os.path.join(CURRENT_DIR, 'cities.csv'))


def test_modules():
    assert ai('module for handy higher-order functions') is functools


def test_sum():
    assert ai('sum of 1 and 1') == 2


def test_sum_bound():
    assert ai('sum of 1 and x', x=10) == 11


def test_translation():
    assert 'bonjour' in ai('translate s to french', s='hello').lower()


def test_multi():
    assert ai('return answer from d', d={'Q': 'bark', 'A': 'dog'}) == 'dog'


# to be hosent, gpt-3.5 is too dumb to understand when to use args and when to creat a func
# I mean you could get it to work on some cases, but there it's not a robust solution
# I think rn best strategy is to say explicitly: use arg if task say so, otherwise create a func
# we splits sync https calls for xdist to perform the best
def test_lambdas_1():
    assert ai('keep the non-primes in l', l=[1, 2, 3, 4, 5, 6, 7, 8, 9]) == [1, 4, 6, 8, 9]


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
    assert ai('read file')(file_path) == 'content'
    assert ai('read file', file=file_path) == 'content'


def test_files_2(file_path):
    assert os.path.exists(file_path)
    assert ai('count number of letter "t" occurence inside file', file=file_path) == 2


def test_session():
    r, sess = ai('sum numbers in x', x=[1, 2, 3, 4, 5], save_session=True)
    assert r == 15
    assert sess.ai('multiply numbers in x') == 120
