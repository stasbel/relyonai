from aiknows import ai


def test_sum():
    assert ai('sum of 1 and x', x=10) == 11


def test_http():
    url = 'https://api.coindesk.com/v1/bpi/currentprice/BTC.json'
    r = ai('get a jsom data from url', url=url)
    assert r['bpi']['USD']['code'] == 'USD'


def test_sets():
    assert ai('unique elements in a - b', a=set([1, 2, 3, 4, 5]), b=set([1, 2, 3])) == {4, 5}


def test_non_primes():
    list_x = [2, 3, 4, 5, 6, 7, 8, 9]
    assert ai('a list of non primes in `list_x`', list_x=list_x) == [4, 6, 8, 9]
