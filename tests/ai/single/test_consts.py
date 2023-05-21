from aiknows import ai


def test_const_1():
    assert ai('number of toes on a two feet') == 10


def test_const_2():
    import os

    assert ai('number of cpus in my computer') == os.cpu_count()


def test_const_3():
    # https://gist.github.com/jboner/2841832
    assert ai('L2 cache latency according to jeff dean table in ns') == 7


def test_const_4():
    # https://www.dcode.fr/divisors-list-number
    assert ai('how many dividers in x', x=2481248) == 96
