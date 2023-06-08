from relyonai import ai


def test_translation():
    assert 'bonjour' in ai('translate s to french', s='hello').lower()
