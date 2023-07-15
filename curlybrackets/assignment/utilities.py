import re
import random
import warnings
from functools import reduce

from pandas import Series, DataFrame, notna, concat
from numpy import logspace, log10, array, ndarray

from ..utilities import get_pool_wave


def clean_regex(s):
    return re.sub(r'(?P<bc>\W)', r'[\g<bc>]', s)


def permute_series(s):
    return random.sample(s.tolist(), s.size)


def add_entry_columns(df, events, pk=None, add_weight=True):
    for e in events:
        if e+'.Entry' not in df.columns:
            if e not in df.columns:
                rows = df.index
            else:
                rows = df.loc[df[e].notna()].index
            if pk:
                df.loc[rows, e+'.Entry'] = df.loc[rows, pk]
            else:
                df.loc[rows, e+'.Entry'] = rows.astype('O')
        if add_weight:
            df[e+'.Weight'] = 1.0/df[e+'.Entry'].map(df[e+'.Entry'].value_counts())
    return df


def add_value_columns(df, events):
    for e in events:
        if e+'.Value' not in df.columns:
            df[e+'.Value'] = 0
        elif df[e+'.Value'].isna().any():
            df[e+'.Value'] = df[e+'.Value'].fillna(0)
    return df


def add_phase_columns(phase_maps, df, events, xchar=None):
    pdfs = [df]
    for e in events:
        if e in phase_maps:
            if xchar:
                # df = df.join(append_x(phase_maps[e], xchar), how='left', on=e).copy()
                pdf = DataFrame(append_x(phase_maps[e], xchar).reindex(df[e]).values,
                                columns=phase_maps[e].columns, index=df.index)
            else:
                # df = df.join(phase_maps[e], how='left', on=e).copy()
                pdf = DataFrame(phase_maps[e].reindex(df[e]).values,
                                columns=phase_maps[e].columns, index=df.index)
            pdfs.append(pdf)
        else:
            # df[e+'..1'] = df[e]
            pdfs.append(df[[e]].rename(columns={e: e+'..1'}))
    return concat(pdfs, axis=1, sort=False)


def count_blocks(sr, xchar=None):
    '''
    Given a competitor's pool schedule (as a pandas Series), count the frequency of each schedule block

    Parameters
    ----------
    sr : pandas.Series
        pandas Series for a competitor's pool schedule
        Series index is phases, Series values are either pool strings or np.nan
    xchar : str 
        Indicator string for an unassigned pool (optional)
    
    Returns
    -------
    pandas.Series
        pandas Series counting the frequncy of each schedule block in the competitor's schedule
        Series index is blocks, Series values are positive integers
    '''
    if xchar is not None:
        sr = sr.loc[sr != xchar]
    waves = sr.dropna().map(get_pool_wave)

    if waves.str.len().max() == 1:
        return waves.value_counts()
    
    blocks = sum([list(w) for w in waves.values], [])
    return Series(blocks).value_counts()


def get_phase_pools(phase_maps, pools, events):
    phase_pools = {}
    for e in events:
        if e in phase_maps:
            ph_pools = phase_maps[e].loc[pools[e]].apply(lambda s: tuple(s.unique()), axis=0)
            phase_pools.update(ph_pools.to_dict())
        else:
            phase_pools[e+'..1'] = pools[e]
    return phase_pools


def get_phase_wave_maps(phase_maps, pools, events):
    wave_maps = {}
    for e in events:
        if e in phase_maps:
            wmap = phase_maps[e].fillna('').applymap(get_pool_wave)
        else:
            wmap = DataFrame({e: pools[e]})
            wmap[e+'..1'] = wmap[e].fillna('').map(get_pool_wave)
            wmap = wmap.set_index(e)
        wave_maps[e] = wmap.drop_duplicates()
    return wave_maps


def maps_from_transitions(phase_transitions, pools=None):
    if pools is None:
        pools = {}

    phase_maps = {}
    for e in phase_transitions:
        if not isinstance(phase_transitions[e], (list, tuple)):
            phase_transitions[e] = [phase_transitions[e]]
        if not all(map(lambda m: isinstance(m, (dict, Series)), phase_transitions[e])):
            raise TypeError(f"Unsupported phase map type for event '{e}', "
                            f"phase maps must be of type dict or Series")
        if e in pools:
            pmap = DataFrame({e: pools[e], e+'..1': pools[e]})
        else:
            if isinstance(phase_transitions[e][0], Series):
                pls = phase_transitions[e][0].index.tolist()
            else:
                pls = phase_transitions[e][0].keys()
            pmap = DataFrame({e: pls, e+'..1': pls})
        for i, pt in enumerate(phase_transitions[e]):
            pmap[e+'..'+str(i+2)] = pmap[e+'..'+str(i+1)].map(pt)
            ppools = sorted(pmap[e+'..'+str(i+2)].unique())
            pmap = pmap.append(DataFrame({e: ppools, e+'..'+str(i+2): ppools}),
                               ignore_index=True, sort=False)
        phase_maps[e] = pmap.set_index(e)

    return phase_maps


def append_x(pmap, xchar):
    if isinstance(pmap, dict):
        return {**pmap, xchar: xchar}
    if isinstance(pmap, Series):
        return concat([pmap, Series([xchar], index=[xchar])])
    if isinstance(pmap, DataFrame):
        return concat([pmap,
                       DataFrame([[xchar] * len(pmap.columns)],
                                 index=[xchar], columns=pmap.columns)],
                      axis=0)
    raise TypeError("Unsupported type: '{}'".format(type(pmap).__name__))


def tau_values(tau, max_iters):
    if tau is None:
        tau = logspace(0, 4, max_iters)
    elif isinstance(tau, (int, float)):
        tau = logspace(0, tau, max_iters)
    elif len(tau) == 2:
        tau = logspace(tau[0], tau[1], max_iters)
    elif len(tau) < max_iters:
        tau = logspace(log10(tau[0]), log10(tau[-1]), max_iters)
        warnings.warn('Fewer tau values than max iterations, changing tau to fix this')
    elif len(tau) > max_iters:
        unused = len(tau) - max_iters
        warnings.warn('More tau values than max iterations, last {} tau values will be unused'.format(unused))

    if not isinstance(tau, ndarray):
        tau = array(tau)

    if tau[0] >= tau[-1]:
        raise ValueError('Beginning tau value is not strictly less than ending tau value')
    elif not (tau[:-1] < tau[1:]).all():
        raise ValueError('Tau values are not continuously increasing')
    elif (tau <= 0).any():
        raise ValueError('Tau values must be positive')

    return tau


# def uniques_from_mixture(mixture):
#  indivs = []
#  for m in mixture:
#      if isinstance(m, (list, tuple)):
#          indivs.extend(m)
#      else:
#          indivs.append(m)
#  return list(set(indivs))


def notna_any(df, cols):
    if isinstance(cols, (list, tuple)):
        return df[cols].notna().any(axis=1)
    else:
        return df[cols].notna()
