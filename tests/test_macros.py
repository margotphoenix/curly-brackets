from io import StringIO

import pytest

import curlybrackets.macros as cbmacro


@pytest.mark.parametrize('uniform_length', [None, 'event', 'all'])
def test_pools_from_schedule_basic(uniform_length):
    schedule = u"""\
Block,SF,MK,BB
A,2,,1
B,2,,1
C,2,2,
D,2,2,
"""
    stream = StringIO(schedule)
    expected = {
        'SF': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'D1', 'D2'],
        'MK': ['C1', 'C2', 'D1', 'D2'],
        'BB': ['A1', 'B1']
    }
    assert cbmacro._read_pools_from_schedule(stream, uniform_length) == expected


@pytest.mark.parametrize('uniform_length, expected',
                         [(None, {'SF': ['A8', 'A9', 'B8', 'B9',
                                         'C8', 'C9', 'D8', 'D9'],
                                  'MK': ['C1', 'C2', 'D1', 'D2'],
                                  'BB': ['A11', 'B11']}),
                          ('event', {'SF': ['A8', 'A9', 'B8', 'B9',
                                            'C8', 'C9', 'D8', 'D9'],
                                     'MK': ['C1', 'C2', 'D1', 'D2'],
                                     'BB': ['A11', 'B11']}),
                          ('all', {'SF': ['A08', 'A09', 'B08', 'B09',
                                          'C08', 'C09', 'D08', 'D09'],
                                   'MK': ['C01', 'C02', 'D01', 'D02'],
                                   'BB': ['A11', 'B11']})])
def test_pools_from_schedule_offset(uniform_length, expected):
    schedule = u"""\
Block,SF,MK,BB
Offset,7,,10
A,2,,1
B,2,,1
C,2,2,
D,2,2,
"""
    stream = StringIO(schedule)
    assert cbmacro._read_pools_from_schedule(stream, uniform_length) == expected


@pytest.mark.parametrize('uniform_length, expected',
                         [(None, {'SF': ['A8', 'A10', 'B8', 'B10',
                                         'C8', 'C10', 'D8', 'D10'],
                                  'MK': ['C1', 'C4', 'D1', 'D4'],
                                  'BB': ['A11', 'B11']}),
                          ('event', {'SF': ['A08', 'A10', 'B08', 'B10',
                                            'C08', 'C10', 'D08', 'D10'],
                                     'MK': ['C1', 'C4', 'D1', 'D4'],
                                     'BB': ['A11', 'B11']}),
                          ('all', {'SF': ['A08', 'A10', 'B08', 'B10',
                                          'C08', 'C10', 'D08', 'D10'],
                                   'MK': ['C01', 'C04', 'D01', 'D04'],
                                   'BB': ['A11', 'B11']})])
def test_pools_from_schedule_step(uniform_length, expected):
    schedule = u"""\
Block,SF,MK,BB
Offset,7,,10
Step,2,3,
A,2,,1
B,2,,1
C,2,2,
D,2,2,
"""
    stream = StringIO(schedule)
    assert cbmacro._read_pools_from_schedule(stream, uniform_length) == expected


def test_pools_from_schedule_subtract():
    schedule = u"""\
Block,KI,BB
Step,,2
A,2,3
B,3,3
B,,-3
C,2,3
"""
    stream = StringIO(schedule)
    expected = {
        'BB': ['A1', 'A3', 'A5', 'B1', 'B5', 'C1', 'C3', 'C5'],
        'KI': ['A1', 'A2', 'B1', 'B2', 'B3', 'C1', 'C2']
    }
    assert cbmacro._read_pools_from_schedule(stream) == expected


def test_pools_from_schedule_shift():
    schedule = u"""\
Block,KI,BB
Offset,10,22
A,2,2
B,3,2
Offset,,20
C,2,4
"""
    stream = StringIO(schedule)
    expected = {
        'BB': ['A23', 'A24', 'B23', 'B24', 'C21', 'C22', 'C23', 'C24'],
        'KI': ['A11', 'A12', 'B11', 'B12', 'B13', 'C11', 'C12']
    }
    assert cbmacro._read_pools_from_schedule(stream) == expected
