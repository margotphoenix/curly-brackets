import pytest

import curlybrackets.utilities as cbutil


@pytest.mark.parametrize('size, expected',
                         [(8, [1, 8, 4, 5, 2, 7, 3, 6]),
                          (9, [1, 16, 8, 9, 4, 13, 5, 12,
                               2, 15, 7, 10, 3, 14, 6, 11])])
def test_seed_order(size, expected):
    assert cbutil.seed_order(size) == expected


@pytest.mark.parametrize('size, expected',
                         [(8, [0, 4, 6, 2, 3, 7, 5, 1]),
                          (9, [0, 8, 12, 4, 6, 14, 10, 2,
                               3, 11, 15, 7, 5, 13, 9, 1])])
def test_reverse_seed_map(size, expected):
    assert list(cbutil.reverse_seed_map(size)) == expected


@pytest.mark.parametrize('seq_list, remove_blanks, expected',
                         [(list('ABCDEFGH'), True, list('AEGCDHFB')),
                          (tuple('ABCDEFGH'), True, tuple('AEGCDHFB')),
                          (list('ABCDEFGH'), False, list('AEGCDHFB')),
                          (['A', '', 'C', 'D', 'E', '', 'G', ''],
                           True, list('AEGCD')),
                          (['A', '', 'C', 'D', 'E', '', 'G', ''],
                           False, list('AEGCD')+['']*3)])
def test_sequential_to_seeds(seq_list, remove_blanks, expected):
    assert cbutil.sequential_to_seeds(seq_list, remove_blanks) == expected


def test_sequential_to_seeds_exception():
    seq_list = list('ABCDEFGHI')
    with pytest.raises(ValueError):
        cbutil.sequential_to_seeds(seq_list)


@pytest.mark.parametrize('seed_list, size, expected',
                         [(list('ABCDEFGH'), None, list('AHDEBGCF')),
                          (tuple('ABCDEFGH'), None, tuple('AHDEBGCF')),
                          (list('ABCDE'), None,
                           ['A', '', 'D', 'E', 'B', '', 'C', '']),
                          (list('ABCD'), None, ['A', 'D', 'B', 'C']),
                          (list('ABCD'), 8,
                           ['A', '', 'D', '', 'B', '', 'C', ''])])
def test_seeds_to_sequential(seed_list, size, expected):
    assert cbutil.seeds_to_sequential(seed_list, size) == expected


def test_widen_bracket():
    sequential = list('ABCD')
    expected = ['A', '', 'B', '', 'C', '', 'D', '']
    assert cbutil.widen_bracket(sequential) == expected


@pytest.mark.parametrize('size, inc, reduced, expected',
                         [(8, 0, False, [[0, 1], [2, 3], [4, 5], [6, 7],
                                         [0, 1, 2, 3], [4, 5, 6, 7],
                                         [0, 1, 2, 3, 4, 5, 6, 7]]),
                          (8, 1, False, [[1, 2], [3, 4], [5, 6], [7, 8],
                                         [1, 2, 3, 4], [5, 6, 7, 8],
                                         [1, 2, 3, 4, 5, 6, 7, 8]]),
                          (8, 1, True, [[[1, 2], [3, 4], [5, 6], [7, 8]],
                                        [[1, 2, 3, 4], [5, 6, 7, 8]],
                                        [[1, 2, 3, 4, 5, 6, 7, 8]]])])
def test_bracket_sections(size, inc, reduced, expected):
    assert cbutil.bracket_sections(size, inc, reduced) == expected
