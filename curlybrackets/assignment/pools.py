import random
from functools import reduce

from pandas import Index, Series, DataFrame
from numpy import exp

from . import compute as c
from . import utilities as u


def _append_dummies(df, pk, events, locations, pools, xchar):
    full_cols = df.columns.tolist()
    loc_cols = list(set(sum((list(l) if isinstance(l, (list, tuple)) else [l] for l in locations), [])))

    for e in events:
        gs = df.groupby(e+'.Entry')[e].first()
        rmndr = gs.isin(pools[e] + [xchar]).sum() % len(pools[e])
        if rmndr > 0:
            ndums = len(pools[e]) - rmndr
            dummy_df = [(['Dummy {} {}'.format(e,j+1)] * 2
                           + [1.0, 0.0, xchar] + ['Dummy'] * len(loc_cols))
                        for j in range(ndums)]
            dummy_cols = [pk, e+'.Entry', e+'.Weight', e+'.Value', e] + loc_cols
            dummy_ix = Index(range(df.index.max()+1, df.index.max()+ndums+1),
                             name=df.index.name)
            df = df.append(DataFrame(dummy_df, index=dummy_ix, columns=dummy_cols), sort=False)

    return df[full_cols]


def _set_initial_state(df, events, pools, xchar):
    open_counts = Series([(df.groupby(e+'.Entry')[e].first() == xchar).sum() for e in events],
                         index=events)
    numer = open_counts * (open_counts-1) / 2
    entries = {}

    for e in events:
        eps = df.groupby(e+'.Entry')[e].first()

        entries[e] = eps.loc[eps == xchar].index.tolist()

        locked_pools = eps.loc[eps.isin(pools[e])].tolist()
        all_pools = pools[e] * (eps.isin(pools[e] + [xchar]).sum() // len(pools[e]))
        for p in locked_pools:
            all_pools.remove(p)
        pool_counts = Series(all_pools).value_counts()
        numer.loc[e] = numer.loc[e] - (pool_counts * (pool_counts-1) / 2).sum()
        eps.loc[eps == xchar] = random.sample(all_pools, len(all_pools))

        df[e] = df[e+'.Entry'].map(eps)

    denom = numer.sum()
    event_cutoffs = (numer / denom).cumsum()

    return df, event_cutoffs, entries


def _make_candidate_swap(df, cutoffs, entries):
    r = random.random()
    e = cutoffs.index[cutoffs.searchsorted(r)]

    curr_pools = df.groupby(e+'.Entry')[e].first()

    chosen = random.sample(entries[e], 2)
    while curr_pools.loc[chosen[0]] == curr_pools.loc[chosen[1]]:
        chosen = random.sample(entries[e], 2)

    newdf = df.copy()
    members = newdf.groupby(e+'.Entry').groups
    newdf.loc[members[chosen[0]], e] = curr_pools.loc[chosen[1]]
    newdf.loc[members[chosen[1]], e] = curr_pools.loc[chosen[0]]

    return newdf, e, chosen


def assign_pools(df, pk, events, locations, pools, external=None,
                 xchar='xx', phase_transitions=None, true_events=None,
                 max_iters=None, iter_check=None, tolerance=0, tau=None,
                 return_full=False, return_scores=False, **kwargs):

    cols = df.columns.tolist()
    rows = df.index.tolist()

    if df[pk].value_counts().max() > 1:
        raise ValueError('Non-unique entries in primary key column')

    if phase_transitions is None:
        phase_transitions = {}
    phase_maps = u.maps_from_transitions(phase_transitions, pools)

    df = u.add_entry_columns(df, events, pk)
    df = u.add_value_columns(df, events)

    df = _append_dummies(df, pk, events, locations, pools, xchar)

    if external:
        df[external] = df[external].fillna('')

    for e in events:
        if (df.groupby(e+'.Entry')[e].nunique(dropna=False) != 1).any():
            raise ValueError('Members of entry in {} have dissimilar assignments'.format(e))

    if max_iters is None:
        max_iters = 50 * df[events].notna().sum().sum()
    tau = u.tau_values(tau, max_iters)

    min_score = c.compute_minimum_score(df, events, locations, pools, xchar=xchar,
                                        phase_maps=phase_maps, external=external,
                                        **kwargs)
    if true_events:
        min_score += c.compute_minimum_score(df, true_events, locations, pools, xchar=xchar,
                                             external=external, phase_distrib_calc='none', **kwargs)

    # Set Initial State
    xdf = df.copy()
    xdf, event_cutoffs, swappable_entries = _set_initial_state(xdf, events, pools, xchar)

    curr_score = c.compute_current_score(xdf, events, locations, pools,
                                         phase_maps=phase_maps, external=external,
                                         **kwargs)
    if true_events:
        curr_score += c.compute_current_score(xdf, true_events, locations, pools,
                                              external=external, phase_distrib_calc='none',
                                              **kwargs)

    counter = 0
    total_swaps_made = 0
    while counter < max_iters and curr_score - min_score > tolerance + 1e-7:
        if iter_check and counter % iter_check == 0:
            print(counter, curr_score, min_score, total_swaps_made)

        newdf, e, chosen = _make_candidate_swap(xdf, event_cutoffs, swappable_entries)

        score_change = c.compute_score_change(xdf, newdf, chosen, e, events, locations, pools,
                                              phase_maps=phase_maps, external=external,
                                              **kwargs)
        if true_events and e in true_events:
            score_change += c.compute_score_change(xdf, newdf, chosen, e, true_events, locations, pools,
                                                   external=external, phase_distrib_calc='none',
                                                   **kwargs)

        q = 1 if score_change < 0 else exp(-tau[counter] * score_change)
        r = random.random()
        if r < q:
            xdf = newdf
            curr_score += score_change
            total_swaps_made += 1

        counter += 1

    if iter_check:
        print(counter, curr_score, min_score, total_swaps_made)

    df = df.loc[rows, cols]

    if return_full:
        xdf = xdf[cols]
    else:
        xdf = xdf.loc[rows, cols]

    if return_scores:
        return xdf, curr_score, min_score
    else:
        return xdf
