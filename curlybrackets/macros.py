import csv
from math import log10


def _read_pools_from_schedule(f, uniform_length=None):
    if uniform_length is None:
        uniform_length = 'none'
    uniform_length = uniform_length.lower()

    reader = csv.reader(f)

    row = next(reader)
    events = row[1:]
    pairs = {e: [] for e in events}
    offsets = {e: 0 for e in events}
    steps = {e: 1 for e in events}

    for row in reader:
        for j,e in enumerate(events):
            try:
                n = int(row[j+1])
            except ValueError:
                continue
            else:
                if row[0].lower() == 'offset':
                    offsets[e] = n
                elif row[0].lower() == 'step':
                    steps[e] = n
                elif n > 0:
                    pairs[e] += [(row[0], steps[e]*i+offsets[e]+1)
                                 for i in range(n)]
                elif n < 0:
                    pairs[e].remove((row[0], -n))

    pools = {}
    if uniform_length == 'event':
        for e in events:
            nmax = int(log10(max([p[1] for p in pairs[e]])))+1
            pools[e] = ['{0}{1:0{nlen}d}'.format(*q, nlen=nmax)
                        for q in pairs[e]]
    elif uniform_length == 'all':
        nmax = max([int(log10(max([p[1] for p in pairs[e]])))+1 for e in events])
        for e in events:
            pools[e] = ['{0}{1:0{nlen}d}'.format(*q, nlen=nmax)
                        for q in pairs[e]]
    else:
        for e in events:
            pools[e] = ['{0}{1:0d}'.format(*q) for q in pairs[e]]

    return pools


def pools_from_schedule(filename, uniform_length=None):
    '''
    uniform length: {'none','event','all'}
    '''
    with open(filename, 'r') as f:
        pools = _read_pools_from_schedule(f, uniform_length)

    return pools
