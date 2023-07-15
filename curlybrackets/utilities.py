

import re
from typing import Tuple, Union


def split_pool_name(pool: str) -> Tuple[Union[str, None], Union[int, None]]:
    """ Split a pool name string into its wave and station components. 
        Example: Pool "CC301" splits into wave "CC" and station "301"

    Parameters
    ----------
    pool : str
        Pool name string in standard letter-number format

    Returns
    -------
    Tuple[Union[str, None], Union[int, None]]
        2-tuple with the separated wave letter and station number, or 
        a (None, None) 2-tuple if pool name could not be split
    """
    m = re.fullmatch(r'([A-Za-z]+)([0-9]+)', pool)
    if m is None:
        return None, None
    w, s = m.groups()
    return w, int(s)


def get_pool_wave(pool: str, raise_for_error: bool = False) -> Union[str, None]:
    """ Get the wave letter from a pool name

    Parameters
    ----------
    pool : str
        Pool name string in standard letter-number format
    raise_for_error : bool 
        Whether to raise an error if pool name is not in standard format, 
        if False (the default) errors are silently ignored

    Returns
    -------
    str
        Wave letter for the pool (or None if `raise_for_error` is False)

    Raises
    ------
    ValueError
        Error raised if pool name is not in standard letter-number format 
        and `raise_for_error` is True
    """
    w, _ = split_pool_name(pool)
    if w is None and raise_for_error:
        raise ValueError(f"Pool name '{pool}' cannot be split or is invalid")
    return w


def get_pool_station(pool: str, raise_for_error: bool = False) -> Union[int, None]:
    """ Get the station number from a pool name as an integer

    Parameters
    ----------
    pool : str
        Pool name string in standard letter-number format
    raise_for_error : bool 
        Whether to raise an error if pool name is not in standard format, 
        if False (the default) errors are silently ignored

    Returns
    -------
    int
        Station number for the pool as an integer (or None if `raise_for_error` is False)

    Raises
    ------
    ValueError
        Error raised if pool name is not in standard letter-number format 
        and `raise_for_error` is True
    """
    _, s = split_pool_name(pool)
    if s is None and raise_for_error:
        raise ValueError(f"Pool name '{pool}' cannot be split or is invalid")
    return s


def seed_order(size):
    order = [1]
    while len(order) < size:
        new_order = []
        L = len(order)*2+1
        for j in order:
            new_order.append(j)
            new_order.append(L-j)
        order = new_order
    return order


def reverse_seed_map(size):
    order = seed_order(size)
    sorted_order, reverse_map = zip(*sorted(zip(order, range(len(order)))))
    return list(reverse_map)


def sequential_to_seeds(seq_list, trim_list=True, trim_match=None):
    if trim_match is None:
        def trim_fn(x): return not x
    elif callable(trim_match):
        trim_fn = trim_match
    else:
        def trim_fn(x): return x == trim_match
    order = seed_order(len(seq_list))
    if len(order) > len(seq_list):
        raise ValueError('Sequence length must be a power of 2')
    sorted_order, seed_list = zip(*sorted(zip(order, seq_list)))
    seed_list = type(seq_list)(seed_list)
    if trim_list:
        while trim_fn(seed_list[-1]):
            seed_list = seed_list[:-1]
    return seed_list


def seeds_to_sequential(seed_list, size=None, fill=''):
    if size is None:
        rmap = reverse_seed_map(len(seed_list))
    else:
        rmap = reverse_seed_map(size)
    if callable(fill):
        fill_fn = fill
    else:
        def fill_fn(x): return fill
    fill_list = [fill_fn(i+1) for i in range(len(rmap)-len(seed_list))]
    filled_list = list(seed_list) + fill_list
    sorted_order, seq_list = zip(*sorted(zip(rmap, filled_list)))
    seq_list = type(seed_list)(seq_list)
    return seq_list


def widen_bracket(bracket):
    '''
    Must be in sequential order.
    '''
    wider_bracket = []
    for player in bracket:
        wider_bracket.append(player)
        wider_bracket.append('')
    return wider_bracket


def bracket_sections(size, inc=0, reduced=False):
    sections = []
    bsize = 1
    while bsize < size:
        bsize *= 2
    j = 1
    while j < bsize:
        j *= 2
        new_sections = [list(range(k, k+j)) for k in range(inc, bsize+inc, j)]
        if reduced:
            sections.append(new_sections)
        else:
            sections += new_sections
    return sections
