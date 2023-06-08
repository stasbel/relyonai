from relyonai import ai


def test_imports_1():
    import functools

    assert ai('standard module for handy higher-order functions') is functools


def test_imports_2():
    import sys

    assert ai('import system stuff standard module') is sys


def test_imports_3():
    from sklearn.svm import LinearSVC

    assert ai('import linear svc from sklearn') is LinearSVC


def test_imports_4():
    import numpy as np

    assert np.allclose(ai('return diagonal unit matrix constructor from numpy')(10), np.eye(10))


def test_imports_5():
    import numpy as np

    assert ai('dynamically import "ones" from module', module='numpy') is np.ones
