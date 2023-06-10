from relyonai import ai


def test_valid_phone_number():
    check_number = ai('input is a valid phone number of format xxx-xxx-xxxx')
    assert check_number('123-456-7890')
    assert not check_number('not a number')


def test_valid_url():
    check_http = ai('check if input is a valid http url')
    assert check_http('http://google.com')
    assert not check_http('not an url')


def test_format_float():
    formatter = ai('format an input float to have 2 digits after .')
    assert formatter(3.1415926) == '3.14'
    assert formatter(3.149) == '3.15'
    assert formatter(3.1) == '3.10'
    assert formatter(3) == '3.00'
    assert formatter(3.99) == '3.99'
    assert formatter(3.50000000) == '3.50'


def test_extractor():
    extractor = ai('extract all xxx-xxx-xxxx format phones from a given text')
    assert extractor('my phone number is 123-456-7890') == ['123-456-7890']


def test_merge_lists():
    assert ai('merge two lists into dict')([1, 2, 3], ['a', 'b', 'c']) == {
        1: 'a',
        2: 'b',
        3: 'c',
    }


def test_filter_in():
    f = ai('filter palindromes away')
    assert f(['hello', 'world', 'racecar', 'foo', 'bar']) == [
        'hello',
        'world',
        'foo',
        'bar',
    ]
    assert f(['abc', 'ccc']) == ['abc']


def test_filter_out_non_primes():
    assert ai('filter non primes out')([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) == [2, 3, 5, 7]


def test_filter_out():
    assert len(ai('filter out every third element')(list(range(900)))) == 600


def test_reverse_list():
    assert ai('reverse a list')(list(range(10))) == list(range(9, -1, -1))


def test_generators():
    def stream():
        for i in range(1000):
            yield i

    # f = ai('leave only even numbers in an input generator')
    f = ai('generate even number from an input generator')
    assert len(list(f(stream()))) == 500
    g = ai('leave numbers at even positions in an input generator')
    assert len(list(g(stream()))) == 500
    assert len(list(g(f(stream())))) == 250
    assert len(list(f(g(stream())))) == 500
