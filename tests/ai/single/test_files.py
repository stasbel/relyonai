from relyonai import ai


def test_files_1(test_file_path):
    assert ai('a function that reads file')(test_file_path) == 'test.txt content'


def test_files_2(test_file_path):
    assert ai('read file at filepath', filepath=test_file_path) == 'test.txt content'


def test_files_3(test_file_path):
    # TesT.TxT conTenT
    assert ai('count number of letter "t" occurence inside file', file=test_file_path) == 6


def test_files_4():
    with open(__file__) as f:
        n_lines = len(f.readlines())
    assert ai('get number of lines in current file') == n_lines
