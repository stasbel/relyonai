from aiknows import ai


def test_sum():
    assert ai('sum of 1 and 1') == 2


def test_sum_bound():
    assert ai('sum of 1 and x', x=10) == 11


def test_translation():
    assert 'bonjour' in ai('translate s to french', s='hello').lower()


def test_multi():
    assert ai('return answer from d', d={'Q': 'bark', 'A': 'dog'}) == 'dog'


def test_lambdas():
    assert ai('filter non primes from l', l=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == [2, 3, 5, 7]
    assert ai('filter non primes out')([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == [2, 3, 5, 7]
    f = ai('filter palindromes out')
    assert f(['hello', 'world', 'racecar', 'foo', 'bar']) == ['hello', 'world', 'foo', 'bar']
    assert f(['abc', 'ccc']) == ['abc']
    assert ai('merge two lists into dict')([1, 2, 3], ['a', 'b', 'c']) == {1: 'a', 2: 'b', 3: 'c'}
    assert ai('unique elements in a - b', a=set([1, 2, 3, 4, 5]), b=set([1, 2, 3])) == {4, 5}
    assert len(ai('filter every third element out')(list(range(900)))) == 600
