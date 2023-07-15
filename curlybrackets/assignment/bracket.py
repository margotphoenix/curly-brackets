import re
import random

from pandas import Series, concat
from numpy import array, exp
from numpy.random import permutation

from . import compute as c
from . import utilities as u

from ..utilities import reverse_seed_map


def _set_initial_state(gp, f, set_with_numpy=True, **kwargs):
    values = gp.groupby(f+'.Entry')[f+'.Value'].mean()
    ranks = values.rank(method='first', ascending=False).astype('int64')
    valrank = concat([values, ranks], axis=1, ignore_index=True)
    if set_with_numpy:
        iseed = valrank.groupby(0)[1].transform(permutation)
    else:
        iseed = valrank.groupby(0)[1].transform(u.permute_series)
    gp[f] = gp[f+'.Entry'].map(iseed)

    if values.nunique() == len(values):
        return gp, None, None

    value_counts = values.value_counts().sort_index()
    numer = value_counts * (value_counts - 1) / 2
    denom = numer.sum()
    value_cutoffs = (numer / denom).cumsum()
    entries = values.reset_index().groupby(f+'.Value')[f+'.Entry'].agg(lambda x: x.tolist())

    return gp, value_cutoffs, entries.to_dict()


def _setup_seedpool_connection(gp, f):
    rmap = reverse_seed_map(gp[f].max())
    N = len(rmap)
    pools = list(range(1, N+1))
    pool_order = Series(array(rmap)+1, index=pools)
    return pools, pool_order


def _make_candidate_swap(gp, f, cutoffs, entries):
    r = random.random()
    v = cutoffs.index[cutoffs.searchsorted(r)]

    curr_seeds = gp.groupby(f+'.Entry')[f].first()

    chosen = random.sample(entries[v], 2)

    newgp = gp.copy()
    members = newgp.groupby(f+'.Entry').groups
    newgp.loc[members[chosen[0]], f] = curr_seeds.loc[chosen[1]]
    newgp.loc[members[chosen[1]], f] = curr_seeds.loc[chosen[0]]

    return newgp, chosen


def assign_bracket_seeds(pdf, e, locations, pk=None, max_iters=None, iter_check=None,
                         tau=None, tolerance=0, verbose=True, **kwargs):

    f = e+'.Seed'
    gp = pdf.rename(columns=lambda s: re.sub('^'+u.clean_regex(e)+'[.]', f+'.', s))

    gp = u.add_entry_columns(gp, [f], pk)
    gp = u.add_value_columns(gp, [f])

    max_iters = max_iters if max_iters is not None else 16 * len(pdf)
    tau = u.tau_values(tau, max_iters)

    gp, value_cutoffs, swappable_entries = _set_initial_state(gp, f, **kwargs)

    if value_cutoffs is None:
        return pdf.join(gp[f], how='left')[f]

    pools, pool_order = _setup_seedpool_connection(gp, f)

    min_score = c.compute_minimum_score(gp, [f], locations, {f: pools},
                                        bracket_accounting='all', skip_schedule=True, **kwargs)

    curr_score = c.compute_current_score(gp, [f], locations, {f: pools},
                                         bracket_accounting='all',
                                         pool_order=pool_order, skip_schedule=True, **kwargs)

    counter = 0
    total_swaps_made = 0
    while counter < max_iters and curr_score - min_score > tolerance + 1e-7:
        if verbose and iter_check and counter % iter_check == 0:
            print(counter, curr_score, min_score, total_swaps_made)

        newgp, chosen = _make_candidate_swap(gp, f, value_cutoffs, swappable_entries)

        score_change = c.compute_score_change(gp, newgp, chosen, f, [f], locations, {f: pools},
                                              bracket_accounting='all',
                                              pool_order=pool_order, skip_schedule=True, **kwargs)

        q = 1 if score_change < 0 else exp(-tau[counter] * score_change)
        r = random.random()
        if r < q:
            gp = newgp
            curr_score += score_change
            total_swaps_made += 1

        counter += 1

    if verbose:
        if iter_check:
            print(counter, curr_score, min_score, total_swaps_made)
        if curr_score - min_score <= tolerance + 1e-7:
            print('Bracket optimized in {:d} iterations'.format(counter))
        else:
            print('Maximum iterations reached, bracket {:.3f} points from optimal'.format(curr_score - min_score))

    return pdf.join(gp[f], how='left')[f]


def positions_from_seeds(psr):
    rmap = reverse_seed_map(psr.max())
    N = len(rmap)
    positions = Series(array(rmap) + 1, index=range(1, N+1))
    return psr.map(positions)
