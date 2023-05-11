from askai import ai


def test_sum():
    assert ai('sum of 1 and 1') == 2


def test_sum_bound():
    assert ai('sum of 1 and x', x=10) == 11
