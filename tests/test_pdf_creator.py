import os
import random
import math
import itertools
import string
from datetime import datetime, timedelta

import pytest

from curlybrackets.pdf.creator import (print_bracket,
                                       print_initial_bracket,
                                       print_continued_bracket,
                                       get_format)


TESTS_DIR = os.path.dirname(os.path.realpath(__file__))
PDF_DIR = os.path.join(TESTS_DIR, 'test-pdfs')


@pytest.fixture(scope='module', autouse=True)
def make_pdfdir():
    if not os.path.isdir(PDF_DIR):
        os.mkdir(PDF_DIR)


@pytest.fixture(scope='module')
def name_list():
    with open(os.path.join(TESTS_DIR, 'tag-list.txt'), 'r') as f:
        names = [line.strip() for line in f]
    random.shuffle(names)
    return itertools.cycle(names)


@pytest.fixture(scope='module')
def game_list():
    with open(os.path.join(TESTS_DIR, 'game-list.txt'), 'r') as f:
        games = [line.strip() for line in f]
    random.shuffle(games)
    return itertools.cycle(games)


@pytest.fixture(scope='module')
def pool_list():
    pools = [f'{x}{n:03d}' for x in string.ascii_uppercase for n in range(1000)]
    random.shuffle(pools)
    return itertools.cycle(pools)


def random_datetime():
    today = datetime.today()
    m = random.choice(range(52 * 7 * 24 * 2)) * 30
    dt = datetime(today.year, today.month, today.day) + timedelta(minutes=m)
    return dt


def random_positions(size, n_adv):
    step = 2 ** math.ceil(math.log2(n_adv))
    x = random.choice(range(0, size, step))
    if n_adv == 2:
        return (x+1, x+2)
    elif n_adv == 3:
        return (x+1, size-x, x+2)
    elif n_adv == 4:
        return (x+1, x+3, x+4, x+2)
    elif n_adv == 6:
        return (x+1, x+5, size-x-2, size-x, x+2, x+6)
    elif n_adv == 8:
        return (x+1, x+5, x+7, x+3, x+4, x+8, x+6, x+2)
    elif n_adv == 12:
        return (x+1, x+5, x+7, x+3, size-x-2, size-x-6, size-x-4, size-x, x+8, x+4, x+2, x+6)


def random_task():
    tasks = ['Competing', 'Judging', 'Commentating', 'Security',
             'Check-In', 'Supervising', 'Panel', 'Community TO']
    return random.choice(tasks)


@pytest.mark.parametrize('n_advance, n_entrants',
                         [(0, [8, 7, 16, 14, 32, 28]),
                          (2, [8, 7, 16, 14, 32, 28]),
                          (3, [16, 14, 32, 28]),
                          (4, [8, 7, 16, 14, 32, 28]),
                          (6, [16, 14, 32, 28]),
                          (8, [16, 14, 32, 28]),
                          (12, [32, 28])])
def test_initial_de_brackets(name_list, game_list, pool_list,
                             n_advance, n_entrants):
    filename = os.path.join(PDF_DIR, f'de_init_{n_advance}adv.pdf')
    entrants, events, pools, judges, dates = zip(*[
        (
            [next(name_list) for _ in range(n)],
            next(game_list),
            next(pool_list),
            next(name_list),
            format(random_datetime(), '%-d %b %Y')
        ) for n in n_entrants
    ])
    notes = [[f'{n} ({random_task()})' for n in es if random.random() < 0.33]
             for es in entrants]

    extra_args = {}
    if n_advance > 0:
        extra_args.update(progressions=[], format_string=[])
        for _ in n_entrants:
            sf = math.ceil(math.log2(n_advance))
            n_pools = 2 ** random.choice(range(3-sf, 9-sf))
            adv_phase_size = n_pools * n_advance
            if adv_phase_size > 64:
                adv_pool_size = 48 if n_advance % 3 == 0 else 64
            else:
                adv_pool_size = adv_phase_size
            positions = random_positions(adv_pool_size, n_advance)
            adv_time = random_datetime()
            adv_phase = f'Top {adv_phase_size}'
            format_string = '<b>{phase:w}</b>'
            if adv_phase_size > adv_pool_size:
                if random.random() < 0.67:
                    adv_phase = 'Round 2'
                adv_pools = (next(pool_list), next(pool_list))
                format_string += ', <b>Pool&nbsp;{pool}</b>'
            else:
                adv_pools = ('', '')
            progs = {(i+1): {
                'phase': adv_phase,
                'starttime': adv_time,
                'pool': adv_pools[positions[i] % 2],
                'position': positions[i],
                'seed': i+1
            } for i in range(n_advance)}
            format_string += ' ({starttime:%a %-I:%M%p}), Line&nbsp;{position}'
            extra_args['progressions'].append(progs)
            extra_args['format_string'].append(format_string)

    print_initial_bracket(filename, entrants, format='double-elimination',
                          n_advance=n_advance, event=events, pool=pools,
                          judge=judges, date=dates, notes=notes, **extra_args)


@pytest.mark.parametrize('n_advance, n_winners, n_losers',
                         [(0, [2, 4, 4, 8, 8, 16], [4, 4, 8, 8, 16, 16]),
                          (2, [4, 8, 16], [4, 8, 16]),
                          (3, [8, 8, 16], [8, 16, 16]),
                          (4, [4, 4, 8, 8, 16], [4, 8, 8, 16, 16]),
                          (6, [8, 8, 16], [8, 16, 16]),
                          (8, [8, 8, 16], [8, 16, 16]),
                          (12, [8, 16], [16, 16])])
def test_continued_de_brackets(name_list, game_list, pool_list,
                               n_advance, n_winners, n_losers):
    filename = os.path.join(PDF_DIR, f'de_cont_{n_advance}adv.pdf')

    in_winners, in_losers = [], []
    for nw, nl in zip(n_winners, n_losers):
        win = [next(pool_list) for _ in range(nw)]
        los = win.copy() if n_advance == 0 else [next(pool_list) for _ in win]
        if nw == nl:
            in_winners.append([f'{p} Winners' for p in win])
            in_losers.append([f'{p} Losers' for p in los])
        elif 2*nw == nl:
            places, dirs = ['3rd Place', '2nd Place'], [1, -1]
            in_winners.append([f'{p} 1st Place' for p in win])
            in_losers.append([
                f'{los[::dirs[j]][i]} {places[j]}'
                for i in range(len(los)) for j in range(2)
            ])
    events, pools, judges, dates = zip(*[
        (
            next(game_list),
            next(pool_list),
            next(name_list),
            format(random_datetime(), '%-d %b %Y')
        ) for _ in n_winners
    ])

    extra_args = {}
    if n_advance > 0:
        extra_args.update(progressions=[], format_string=[])
        for _ in n_winners:
            sf = math.ceil(math.log2(n_advance))
            n_pools = 2 ** random.choice(range(0, 7-sf))
            adv_phase_size = n_pools * n_advance
            positions = random_positions(adv_phase_size, n_advance)
            adv_time = random_datetime()
            adv_phase = f'Top {adv_phase_size}'
            progs = {(i+1): {
                'phase': adv_phase.replace(' ', '&nbsp;'),
                'starttime': adv_time,
                'pools': adv_phase,
                'position': positions[i],
                'seed': i+1
            } for i in range(n_advance)}
            format_string = ('<b>{phase}</b> '
                             '({starttime:%a %-I:%M%p}), '
                             'Line&nbsp;{position}')
            extra_args['progressions'].append(progs)
            extra_args['format_string'].append(format_string)

    print_continued_bracket(filename, in_winners, in_losers,
                            n_advance=n_advance, event=events, pool=pools,
                            judge=judges, date=dates, **extra_args)


def test_rr_grids(name_list, game_list, pool_list):
    n_entrants = [4, 7, 10, 10, 11, 11]
    n_advance = [3, 3, 0, 4, 0, 4]

    filename = os.path.join(PDF_DIR, 'rr_grids.pdf')
    entrants, events, pools, judges, dates = zip(*[
        (
            [next(name_list) for _ in range(n)],
            next(game_list),
            next(pool_list),
            next(name_list),
            format(random_datetime(), '%-d %b %Y')
        ) for n in n_entrants
    ])
    notes = [[f'{n} ({random_task()})' for n in es if random.random() < 0.33]
             for es in entrants]

    progressions = []
    format_string = '<b>{phase}</b>,&nbsp;<b>Pool&nbsp;{pool}</b>'
    for na in n_advance:
        d = random.randint(1, 5)
        prog = {(i+1): {'phase': f'Division&nbsp;{d}',
                        'pool': next(pool_list),
                        'seed': i+1} for i in range(na)}
        progressions.append(prog)

    print_bracket(filename, entrants, format='round-robin', event=events,
                  pool=pools, judge=judges, date=dates, notes=notes,
                  progressions=progressions, format_string=format_string)


@pytest.mark.parametrize('fmt, n_entrants',
                         [('d', [8, 7, 16, 14, 32, 28, 64, 56]),
                          ('s', [8, 7, 16, 14, 32, 28])])
def test_initial_playpool_brackets(name_list, game_list, fmt, n_entrants):
    filename = os.path.join(PDF_DIR, f'{fmt}e_init_playpool.pdf')
    entrants, labels, judges, dates = zip(*[
        (
            [next(name_list) for _ in range(n)],
            next(game_list),
            next(name_list),
            format(random_datetime(), '%-d %b %Y')
        ) for n in n_entrants
    ])

    print_initial_bracket(filename, entrants, format=fmt, source='playpool',
                          label=labels, judge=judges, date=dates)


@pytest.mark.parametrize('fmt, n_winners, n_losers',
                         [('d', [16, 32], [32, 32])])
def test_continued_playpool_brackets(name_list, game_list, pool_list,
                                     fmt, n_winners, n_losers):
    filename = os.path.join(PDF_DIR, f'{fmt}e_cont_playpool.pdf')

    in_winners, in_losers = [], []
    for nw, nl in zip(n_winners, n_losers):
        win = [next(pool_list) for _ in range(nw)]
        los = win.copy()
        if nw == nl:
            in_winners.append([f'{p} Winners' for p in win])
            in_losers.append([f'{p} Losers' for p in los])
        elif 2*nw == nl:
            places, dirs = ['3rd Place', '2nd Place'], [1, -1]
            in_winners.append([f'{p} 1st Place' for p in win])
            in_losers.append([
                f'{los[::dirs[j]][i]} {places[j]}'
                for i in range(len(los)) for j in range(2)
            ])
    labels, judges, dates = zip(*[
        (
            next(game_list),
            next(name_list),
            format(random_datetime(), '%-d %b %Y')
        ) for n in n_winners
    ])

    print_continued_bracket(filename, in_winners, in_losers, format=fmt,
                            label=labels, judge=judges, date=dates)


def test_playpool_grids(name_list, game_list):
    n_entrants = [4, 7, 10]

    filename = os.path.join(PDF_DIR, 'rr_playpool.pdf')
    entrants, labels, judges, dates = zip(*[
        (
            [next(name_list) for _ in range(n)],
            next(game_list),
            next(name_list),
            format(random_datetime(), '%-d %b %Y')
        ) for n in n_entrants
    ])

    print_bracket(filename, entrants, format='r', source='playpool',
                  label=labels, judge=judges, date=dates)


@pytest.mark.parametrize('byes', ['show', 'number'])
def test_byes(name_list, game_list, pool_list, byes):
    filename = os.path.join(PDF_DIR, f'de_byes_{byes}.pdf')

    n_entrants = [11, 21]
    entrants, pools = zip(*[
        (
            [next(name_list) for _ in range(n)],
            next(pool_list)
        ) for n in n_entrants
    ])
    event = next(game_list)

    print_initial_bracket(filename, entrants, format='double-elimination',
                          n_advance=0, byes=byes, event=event, pool=pools)


def test_bracket_size(name_list, game_list, pool_list):
    filename = os.path.join(PDF_DIR, 'de_bracket_size.pdf')

    n_entrants = [9, 8, 7]
    bracket_size = 16
    entrants, pools = zip(*[
        (
            [next(name_list) for _ in range(n)],
            next(pool_list)
        ) for n in n_entrants
    ])
    event = next(game_list)

    print_initial_bracket(filename, entrants, n_advance=0,
                          bracket_size=bracket_size, event=event, pool=pools)


def test_continued_bracket_exceptions(name_list):
    filename = os.path.join(PDF_DIR, 'cont_exceptions.pdf')

    n_winners, n_losers = [8, 16], [16]
    in_winners = [[next(name_list) for _ in range(n)] for n in n_winners]
    in_losers = [[next(name_list) for _ in range(n)] for n in n_losers]
    with pytest.raises(ValueError):
        print_continued_bracket(filename, in_winners, in_losers)

    n_winners, n_losers = [8, 16], [16, 16]
    in_winners = [[next(name_list) for _ in range(n)] for n in n_winners]
    in_losers = [[next(name_list) for _ in range(n)] for n in n_losers]
    with pytest.raises(ValueError):
        print_continued_bracket(filename, in_winners, in_losers,
                                format='round-robin')
    with pytest.raises(NotImplementedError):
        print_continued_bracket(filename, in_winners, in_losers,
                                name_order='seed')

    n_winners, n_losers = [8, 12, 16], [16, 16, 16]
    in_winners = [[next(name_list) for _ in range(n)] for n in n_winners]
    in_losers = [[next(name_list) for _ in range(n)] for n in n_losers]
    with pytest.raises(ValueError):
        print_continued_bracket(filename, in_winners, in_losers)


@pytest.mark.parametrize('format',
                         ['double-elimination',
                          'single-elimination',
                          'round-robin'])
def test_get_format(format):
    assert get_format(format) == format
    assert get_format(format.upper()) == format
    assert get_format(format.split('-')[0]) == format
    assert get_format(format.upper()[0]) == format


def test_get_format_exception():
    with pytest.raises(TypeError):
        get_format('waterfall')
