from aiknows import ai


def test_sum():
    assert ai('sum of 1 and 1') == 2


def test_sum_bound():
    assert ai('sum of 1 and x', x=10) == 11


def test_translation():
    assert ai('translate s to french', s='hello').lower() == 'bonjour'


def test_multi():
    assert ai('return answer from d', d={'Q': 'bark?', 'A': 'dog'}) == 'dog'
