import re
import random
import warnings
from functools import reduce
from itertools import combinations
from math import ceil
from collections.abc import Sequence

from pandas import Series, DataFrame, concat
from numpy import array, exp, log2
from numpy.random import permutation

from . import compute as c
from . import utilities as u

from ..utilities import get_pool_wave, reverse_seed_map, bracket_sections


class ReorderList(Sequence):
    def __init__(self, method, npools):
        if not self._legal_reorder_method(method, npools):
            raise TypeError('Reorder method not a legal reordering')

        _reducer = lambda x: reduce(lambda a, b: a + b, x, [])
        if method == 'frozen':
            _list = []
            _method = method
        elif method == 'strict':
            _secs = bracket_sections(npools, 1, True)
            _list = [(_reducer(s), _reducer([x[::-1] for x in s])) for s in _secs]
            _method = method
        elif method == 'semistrict':
            _secs = bracket_sections(npools, 1)
            _list = [(s, s[::-1]) for s in _secs]
            _method = method
        elif method == 'relaxed':
            _list = [([p, q], [q, p]) for p, q in combinations(range(1, npools+1), 2)]
            _method = method
        else:
            _list = method
            _method = 'custom'

        self._list = _list
        self.method = _method

    def __len__(self):
        return len(self._list)

    def __getitem__(self, index):
        return self._list.__getitem__(index)

    @staticmethod
    def _legal_reorder_method(method, npools):
        if method in ['frozen', 'strict', 'semistrict', 'relaxed']:
            return True
        elif not isinstance(method, list):
            return False
        for z in method:
            if not isinstance(z, (list,tuple)):
                return False
            elif len(z) != 2:
                return False
            elif set(z[0]) != set(z[1]):
                return False
            for v in z:
                if len(v) != len(set(v)):
                    return False
            for w in z[0]:
                if not isinstance(w, int) or w <= 0 or w > npools:
                    return False
        return True


def _get_reorder_options(reorder_method, events, pools):
    if not isinstance(reorder_method, dict):
        if reorder_method not in ['frozen', 'strict', 'semistrict', 'relaxed']:
            reorder_method = 'semistrict'
        reorder_method = {e: reorder_method for e in events}

    reorder_options = {}
    for e in events:
        try:
            reorder_options[e] = ReorderList(reorder_method.get(e, 'frozen'),
                                             len(pools[e]))
        except TypeError:
            raise TypeError('Reorder method for event {} not a legal reordering'.format(e))
    return reorder_options


def _get_start_order(pool_order, events, pools, reorder_options, set_with_numpy=True, **kwargs):
    if isinstance(pool_order, dict):
        pool_order.update({e: (lambda s: s) for e in events if e not in pool_order})
    elif pool_order is not None:
        pool_order = {e: pool_order for e in events}
    else:
        pool_order = {e: (lambda s: s) for e in events}

    start_order = {}
    for e in events:
        if isinstance(pool_order[e], Series):
            order = pool_order[e].loc[pools[e]].sort_values().index.tolist()
        elif isinstance(pool_order[e], dict):
            order = sorted(pools[e], key=pool_order[e].get)
        else:
            order = sorted(pools[e], key=pool_order[e])
        order_ser = Series(order, index=range(1, len(pools[e])+1))
        if reorder_options[e].method == 'strict':
            flip_chosen = random.choice(reorder_options[e])
            order_ser.loc[flip_chosen[0]] = order_ser.loc[flip_chosen[1]].values
        elif reorder_options[e].method == 'semistrict':
            for flip in reversed(reorder_options[e]):
                if random.random() < 0.5:
                    order_ser.loc[flip[0]] = order_ser.loc[flip[1]].values
        elif reorder_options[e].method == 'relaxed':
            if set_with_numpy:
                order_ser.loc[:] = permutation(order_ser)
            else:
                order_ser.loc[:] = u.permute_series(order_ser)
        elif reorder_options[e].method == 'custom':
            nflips = random.randint(0, len(reorder_options[e]))
            flips_chosen = random.sample(reorder_options[e], nflips)
            for flip in flips_chosen:
                order_ser.loc[flip[0]] = order_ser.loc[flip[1]].values
        start_order[e] = order_ser
    return start_order


_has_mixed_values = lambda s: s.isna().any() and s.notna().any()


def _split_seeds(df, events):
    sdix = Series(False, index=df.index)
    for e in events:
        sdix |= (df[e].notna() & df[e+'.Value'].notna())
    sdf = df.loc[sdix].copy()
    udf = df.loc[~sdix].copy()
    return sdf, udf


def _set_initial_seed_state(df, events, pools, reorder_options, set_with_numpy=True, **kwargs):
    swappable_entries = {}
    value_cutoffs = {}
    swapevent_numer = {}
    for e in events:
        values = df.groupby(e+'.Entry')[e+'.Value'].mean().dropna()
        ranks = values.rank(method='first', ascending=False).astype('int64')
        valrank = concat([values, ranks], axis=1, ignore_index=True)
        if set_with_numpy:
            iseed = valrank.groupby(0)[1].transform(permutation)
        else:
            iseed = valrank.groupby(0)[1].transform(u.permute_series)
        df[e+'.Seed'] = df[e+'.Entry'].map(iseed)

        value_counts = values.value_counts().sort_index()
        # numer = value_counts*(value_counts-1)/2
        numer = value_counts - 1
        denom = numer.sum()
        if denom > 0:
            value_cutoffs[e] = (numer / denom).cumsum()
            entries = values.reset_index().groupby(e+'.Value')[e+'.Entry'].agg(lambda x: x.tolist())
            swappable_entries[e] = entries.to_dict()
        swapevent_numer[e] = {'Seed': denom}
        if len(reorder_options[e]) > 0 and len(pools[e]) > 1:
            swapevent_numer[e].update({'Order': len(pools[e])})
        else:
            swapevent_numer[e].update({'Order': 0})

    swapevent_numer = DataFrame(swapevent_numer).stack()
    swapevent_denom = swapevent_numer.sum()
    swapevent_cutoffs = (swapevent_numer/swapevent_denom).cumsum()

    return df, swapevent_cutoffs, value_cutoffs, swappable_entries


def _setup_seedpool_connection(df, events, pools, bracket_event=True,
                               skip_bracket_calc=False, **kwargs):
    if isinstance(bracket_event, dict):
        bracket_event.update({e: True for e in events if e not in bracket_event})
    else:
        bracket_event = {e: bool(bracket_event) for e in events}
    if isinstance(skip_bracket_calc, dict):
        skip_bracket_calc.update({e: False for e in events if e not in skip_bracket_calc})
    else:
        skip_bracket_calc = {e: bool(skip_bracket_calc) for e in events}

    seed_smap = {}
    sd_events = []
    sd_pools = {}
    sd_order = {}
    for e in events:
        if not bracket_event[e] or 2**int(log2(len(pools[e]))) != len(pools[e]):
            N = ceil(df[e+'.Seed'].max() / len(pools[e])) * len(pools[e])
            rser = Series(range(N), index=range(1, N+1))
            seed_smap[e] = (rser * ((-1)**((rser//len(pools[e])) % 2)) -
                                ((rser//len(pools[e])) % 2)) % len(pools[e]) + 1
        else:
            rmap = reverse_seed_map(df[e+'.Seed'].max())
            N = len(rmap)
            rser = Series(array(rmap), index=range(1, N+1))
            seed_smap[e] = rser * len(pools[e]) // N + 1
            if not skip_bracket_calc[e]:
                sd_events.append(e+'.Seed')
                sd_pools[e+'.Seed'] = list(range(1, N+1))
                sd_order[e+'.Seed'] = rser + 1
    return sd_events, sd_pools, sd_order, seed_smap


def _add_seed_entry_columns(df, events):
    for e in events:
        seeded = df[e+'.Seed'].notna()
        df.loc[seeded, e+'.Seed.Entry'] = df.loc[seeded, e+'.Entry']
        df.loc[seeded, e+'.Seed.Weight'] = df.loc[seeded, e+'.Weight']
    return df


def _set_initial_pool_state(df, events, seed_smap, pool_order):
    for e in events:
        seeded = df[e+'.Seed'].notna()
        df.loc[seeded, e] = df.loc[seeded, e+'.Seed'].map(seed_smap[e]).map(pool_order[e])
    return df


def _select_swap_type(swapevent_cutoffs):
    r = random.random()
    swap, e = swapevent_cutoffs.index[swapevent_cutoffs.searchsorted(r)]
    # while swap == 'Seed' and len(pools[e]) == 1:
    #     r = random.random()
    #     swap, e = swapevent_cutoffs.index[swapevent_cutoffs.searchsorted(r)]
    return swap, e


def _make_seed_swap(df, e, cutoffs, entries):
    r = random.random()
    v = cutoffs.index[cutoffs.searchsorted(r)]

    f = e+'.Seed'
    curr_seeds = df.groupby(f+'.Entry')[f].first()
    curr_pools = df.groupby(e+'.Entry')[e].first()

    chosen = random.sample(entries[v], 2)

    newdf = df.copy()
    members = newdf.groupby(f+'.Entry').groups
    newdf.loc[members[chosen[0]], f] = curr_seeds.loc[chosen[1]]
    newdf.loc[members[chosen[1]], f] = curr_seeds.loc[chosen[0]]
    newdf.loc[members[chosen[0]], e] = curr_pools.loc[chosen[1]]
    newdf.loc[members[chosen[1]], e] = curr_pools.loc[chosen[0]]

    return newdf, chosen, (curr_pools.loc[chosen].nunique() == 1)


def _make_order_swap(pool_order, df, e, reorder_options, seed_smap):
    new_pool_order = pool_order.copy()

    flip = random.choice(reorder_options)
    new_pool_order.loc[flip[0]] = new_pool_order.loc[flip[1]].values

    # Get changed indexes
    f = e+'.Seed'
    curr_seeds = df.groupby(f+'.Entry')[f].first()
    is_flipped = curr_seeds.map(seed_smap).isin(flip[0])
    flipped = curr_seeds.loc[is_flipped].index.tolist()

    # Map seeds to pools
    newdf = df.copy()
    seeded = newdf[f].notna()
    newdf.loc[seeded, e] = newdf.loc[seeded, f].map(seed_smap).map(new_pool_order)

    return new_pool_order, newdf, flipped


def assign_seed_pools(df, pk, events, locations, pools, external=None,
                      xchar='xx', phase_transitions=None, init_pool_order=None,
                      reorder_method=None, true_events=None,
                      max_iters=None, iter_check=None, tolerance=0, tau=None,
                      return_scores=False, return_order=True, return_seeds=False, **kwargs):

    cols = df.columns.tolist()
    rows = df.index.tolist()

    if df[pk].value_counts().max() > 1:
        raise ValueError('Non-unique entries in primary key column')

    if phase_transitions is None:
        phase_transitions = {}
    phase_maps = u.maps_from_transitions(phase_transitions, pools)

    df = u.add_entry_columns(df, events, pk)

    if external is not None:
        df[external] = df[external].fillna('')

    key_events = [e for e in events if e+'.Value' in df.columns and df[e+'.Value'].notna().any()]
    key_event_values = [e+'.Value' for e in key_events]

    if (df[key_events].notna() & (df[key_events] != xchar)).any().any():
        raise ValueError('Cannot pre-assign pools for seeded player assignment')
    if (df[key_event_values] <= 0).any().any():
        raise ValueError('Seed values cannot be negative')

    reorder_options = _get_reorder_options(reorder_method, key_events, pools)
    curr_pool_order = _get_start_order(init_pool_order, key_events, pools, reorder_options, **kwargs)

    for k in key_events:
        if df.groupby(k+'.Entry')[k+'.Value'].agg(_has_mixed_values).any():
            warnings.warn('Members of team(s) in {} have both null and non-null values, may have unintended effects'.format(k))

    sdf, udf = _split_seeds(df, key_events)

    if max_iters is None:
        max_iters = 100 * sdf[key_events].notna().sum().sum()
    tau = u.tau_values(tau, max_iters)

    # Set Initial State
    sdf, swapevent_cutoffs, value_cutoffs, swappable_entries = _set_initial_seed_state(sdf, key_events, pools, 
                                                                                       reorder_options, **kwargs)
    sd_events, sd_pools, sd_order, seed_smap = _setup_seedpool_connection(sdf, key_events, pools, **kwargs)

    sdf = sdf.rename(columns=lambda s: re.sub(r'[.]Value$', '.Seed.Value', s))
    sdf = u.add_value_columns(sdf, events)
    sdf = _add_seed_entry_columns(sdf, key_events)

    # Compute minimum score
    min_score_seed = c.compute_minimum_score(sdf, sd_events, locations, sd_pools,
                                             bracket_accounting='all', skip_schedule=True,
                                             phase_distrib_calc='first', **kwargs)
    min_score_pool = c.compute_minimum_score(sdf, events, locations, pools, xchar=xchar,
                                             phase_maps=phase_maps, external=external,
                                             phase_distrib_calc='max', **kwargs)
    if true_events:
        min_score_pool += c.compute_minimum_score(sdf, true_events, locations, pools,
                                                  xchar=xchar, external=external,
                                                  phase_distrib_calc='none', **kwargs)

    if iter_check:
        print(min_score_seed, min_score_pool)

    scale_factor = 1 if min_score_seed <= min_score_pool else min_score_pool / min_score_seed

    min_score = min_score_seed * scale_factor + min_score_pool

    #map seeds to pools
    sdf = _set_initial_pool_state(sdf, key_events, seed_smap, curr_pool_order)

    #compute current score
    curr_score_seed = c.compute_current_score(sdf, sd_events, locations, sd_pools,
                                              bracket_accounting='all', pool_order=sd_order,
                                              skip_schedule=True, phase_distrib_calc='first', **kwargs)
    curr_score_pool = c.compute_current_score(sdf, events, locations, pools, xchar=xchar,
                                              phase_maps=phase_maps, external=external,
                                              min_schedule_calc=True, phase_distrib_calc='max', **kwargs)
    if true_events:
        curr_score_pool += c.compute_current_score(sdf, true_events, locations, pools, xchar=xchar,
                                                   external=external, min_schedule_calc=True,
                                                   phase_distrib_calc='none', **kwargs)

    if iter_check:
        print(curr_score_seed, curr_score_pool)

    curr_score = curr_score_seed * scale_factor + curr_score_pool

    counter = 0
    swaps_made = {'Seed': 0, 'Order': 0}
    while counter < max_iters and curr_score - min_score > tolerance + 1e-7:
        if iter_check and counter % iter_check == 0:
            print(counter, curr_score, min_score, swaps_made['Seed'], swaps_made['Order'])

        swap, e = _select_swap_type(swapevent_cutoffs)

        if swap == 'Seed':
            newdf, chosen, same_pool = _make_seed_swap(sdf, e, value_cutoffs[e], swappable_entries[e])
            new_pool_order = curr_pool_order[e]

            # get seed score change
            if e+'.Seed' in sd_events:
                score_change_seed = c.compute_score_change(sdf, newdf, chosen, e+'.Seed', [e+'.Seed'], locations, sd_pools,
                                                           bracket_accounting='all', pool_order=sd_order[e+'.Seed'],
                                                           skip_schedule=True, phase_distrib_calc='first', **kwargs)
            else:
                score_change_seed = 0
            # get pool score change
            if not same_pool:
                score_change_pool = c.compute_score_change(sdf, newdf, chosen, e, events, locations, pools,
                                                           xchar=xchar, phase_maps=phase_maps, external=external,
                                                           min_schedule_calc=True, phase_distrib_calc='max', **kwargs)
                if true_events:
                    score_change_pool += c.compute_score_change(sdf, newdf, chosen, e, true_events, locations,
                                                                pools, xchar=xchar, external=external,
                                                                min_schedule_calc=True, phase_distrib_calc='none', **kwargs)
            else:
                score_change_pool = 0

            score_change = score_change_seed * scale_factor + score_change_pool

        elif swap == 'Order':
            new_pool_order, newdf, flipped = _make_order_swap(curr_pool_order[e], sdf, e, reorder_options[e], seed_smap[e])

            #get pool score change
            if not (curr_pool_order[e].map(get_pool_wave) == new_pool_order.map(get_pool_wave)).all():
                score_change = c.compute_score_change(sdf, newdf, flipped, e, events, locations, pools,
                                                      xchar=xchar, phase_maps=phase_maps, external=external,
                                                      min_schedule_calc=True, phase_distrib_calc='none', **kwargs)
                if true_events:
                    score_change += c.compute_score_change(sdf, newdf, flipped, e, true_events, locations,
                                                           pools, xchar=xchar, external=external,
                                                           min_schedule_calc=True, phase_distrib_calc='none', **kwargs)
            else:
                score_change = 0

        q = 1 if score_change < 0 else exp(-tau[counter] * score_change)
        r = random.random()
        if r < q:
            sdf = newdf
            curr_pool_order[e] = new_pool_order
            curr_score += score_change
            swaps_made[swap] += 1

        counter += 1

    if iter_check:
        print(counter, curr_score, min_score, swaps_made['Seed'], swaps_made['Order'])

    # Merge back into df
    sdf = sdf.append(udf, sort=False).sort_index()

    # Return df AND current orders
    df = df.loc[rows, cols]

    sdf = sdf.loc[rows]

    if return_seeds:
        sdf = sdf[cols + [k+'.Seed' for k in key_events]]
    else:
        sdf = sdf[cols]

    if return_order:
        if return_scores:
            return sdf, curr_pool_order, curr_score, min_score
        else:
            return sdf, curr_pool_order
    else:
        if return_scores:
            return sdf, curr_score, min_score
        else:
            return sdf
