from aiknows import gpt


def test_progression():
    prompt = """\
Q: 1
A: 2
Q: 2
A: 4
Q: 4
A: 8
Q: 8
A:\
"""
    assert int(gpt(prompt, t=0.0)) == 16
