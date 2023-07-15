import re
import warnings
from functools import reduce, partial
from math import factorial

from pandas import Series, DataFrame, Index
from numpy import array, unique, where, zeros, infty

from . import utilities as u


_pull_event = lambda s: re.sub(r'[.]{2}[1-9][0-9]*$', '', s)


def _optimal_uniform_partition(nbins, nitems):
    m = nbins
    c = nitems
    return array([c//m] * m) + array([1] * (c%m) + [0] * (m - c%m))


def _optimal_weight_partition(nbins, weights):
    '''
    Note: This algorithm is not a perfect algorithm, as there are some
    extremely rare cases that will cause it to not return an optimal
    partition. However, those cases are highly unlikely to come up in
    any real-world use of this code that I feel comfortable that this
    algorithm is sufficient.
    '''
    wgt,ct = unique(weights, return_counts=True)
    if len(wgt) == 1:
        return wgt[0]*_optimal_uniform_partition(nbins,len(weights))
    bins = zeros(nbins)
    for w,c in reversed(list(zip(wgt,ct))):
        j = c
        while j > 0:
            ix = where(bins==bins.min())[0]
            k = min(j,len(ix))
            part = zeros(nbins)
            part[ix[:k]] = w
            bins += part
            j -= k
    return bins


def compute_schedule_minimum(sr, phases, wave_maps, keep_assigned=False, xchar=None,
                             external=None, splitchar=None, wave_order=None, scm=2.0, xcm=8.0, **kwargs):
    splitter = list if splitchar is None else partial(str.split, sep=splitchar)
    ext_conflicts = splitter('' if external is None else sr[external])
    if keep_assigned and xchar is None:
        warnings.warn('xchar value should be set if keep_assigned is True')

    phases_entered = sr[phases].dropna()
    waves_possible = sorted(set(sum(
        (wave_maps[_pull_event(p)][p].dropna().tolist() for p in phases_entered.index), [])))
    blocks_possible = sorted(set(sum((list(x) for x in waves_possible), [])))
    
    block_sr_external = Series({b: int(b in ext_conflicts) for b in blocks_possible})
    block_sr_current = Series(0, index=blocks_possible)
    if keep_assigned:
        phases_unassigned = phases_entered.loc[phases_entered == xchar].index.tolist()
        block_sr_current = block_sr_current.add(u.count_blocks(phases_entered, xchar), fill_value=0)
    else:
        phases_unassigned = phases_entered.index.tolist()
    events_unassigned = list(set((_pull_event(p) for p in phases_unassigned)))
    wmaps_ua = {e: wave_maps[e].dropna() for e in events_unassigned}

    while phases_unassigned:
        block_sr_slope = (scm * ((block_sr_current+1).map(factorial) - block_sr_current.map(factorial)) 
                            + xcm * block_sr_external)
        # wave_sr_slope = {w: block_sr_slope[list(w)].sum() for w in waves_possible}
        min_slope = infty
        for e in events_unassigned:
            e_slope = wmaps_ua[e].applymap(lambda w: block_sr_slope[list(w)].sum()).sum(axis=1)
            if e_slope.min() < min_slope:
                min_slope = e_slope.min()
                min_noptions = infty
            if e_slope.min() == min_slope:
                e_noptions = (e_slope == min_slope).sum()
                if e_noptions < min_noptions:
                    min_noptions = e_noptions
                    events_preferred = []
                    wmaps_pref = {}
                if e_noptions == min_noptions:
                    events_preferred.append(e)
                    wmaps_pref[e] = wmaps_ua[e].loc[e_slope == min_slope]
        phases_preferred = [p for p in phases_unassigned if _pull_event(p) in events_preferred]
        waves_preferred = sorted(set(sum(
            (wmaps_pref[_pull_event(p)][p].tolist() for p in phases_preferred), [])))
        blocks_preferred = sorted(set(sum((list(x) for x in waves_preferred), [])))

        if wave_order is not None:
            waves_preferred = [w for w in wave_order if w in waves_preferred]
        for w in waves_preferred:
            phases_chosen = [p for p in phases_preferred if w in wmaps_pref[_pull_event(p)][p].tolist()]
            if len(phases_chosen) > 0:
                phases_preferred = phases_chosen
            if len(phases_preferred) == 1:
                break
        phase_chosen = phases_preferred[0]
        wave_chosen = waves_preferred[0]
        event_chosen = _pull_event(phase_chosen)
        phases_unassigned.remove(phase_chosen)
        events_unassigned = list(set((_pull_event(p) for p in phases_unassigned)))
        if event_chosen in events_unassigned:
            wmap_ua_chosen = wmaps_ua[event_chosen]
            wmaps_ua[event_chosen] = wmap_ua_chosen.loc[wmap_ua_chosen[phase_chosen] == wave_chosen].drop(phase_chosen, axis=1)
        else:
            del wmaps_ua[event_chosen]
        block_sr_current.loc[list(wave_chosen)] += 1

    block_vc = block_sr_current.loc[block_sr_current > 0]
    min_contrib = (scm * (block_vc.map(factorial).sum() - len(block_vc))
                     + xcm * block_vc.reindex(ext_conflicts).fillna(0).sum())

    return min_contrib


def compute_schedule_contribution(sr, phases, external=None,
                                  splitchar=None, scm=2.0, xcm=8.0, **kwargs):
    splitter = list if splitchar is None else partial(str.split, sep=splitchar)
    ext_conflicts = splitter('' if external is None else sr[external])

    block_vc = u.count_blocks(sr[phases])
    contrib = (scm * (block_vc.map(factorial).sum() - len(block_vc))
                 + xcm * block_vc.reindex(ext_conflicts).fillna(0).sum())

    return contrib


def compute_distrib_minimum(entrant_weights, npools, account_for_bracket=False):
    dist_min = _optimal_weight_partition(npools, entrant_weights).std() #ddof = 0
    if account_for_bracket:
        nleft = npools
        while nleft/2 > 1:
            nleft //= 2
            dist_min += _optimal_weight_partition(nleft, entrant_weights).std() #ddof = 0
    return dist_min


def compute_distrib_contribution(pool_counts, pools, account_for_bracket=False):
    dist = Series(0.0, index=pools)
    dist = dist.add(pool_counts, fill_value=0.0)
    dist_values = dist.sort_index().values
    dist_score = dist_values.std() #ddof = 0
    if account_for_bracket:
        while len(dist_values) > 2:
            dist_values = dist_values[0::2] + dist_values[1::2]
            dist_score += dist_values.std() #ddof = 0
    return dist_score


def compute_minimum_score(df, events, locations, pools, xchar=None,
                          phase_maps=None, bracket_accounting='none',
                          skip_schedule=False, phase_distrib_calc='first',
                          schedule_weight_col=None, location_thold=1, **kwargs):
    # Note: pool_order not used in calculating minimum score
    # Note: bracket_accounting: {'all','ranked','none'}
    if phase_maps is None:
        phase_maps = {}

    dfc = df.copy()
    dfc = u.add_phase_columns(phase_maps, dfc, events, xchar)
    ph_pools = u.get_phase_pools(phase_maps, pools, events)
    phases = dfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    min_score = 0.0
    if not skip_schedule:
        wave_maps = u.get_phase_wave_maps(phase_maps, pools, events)
        schedule_scores = dfc.apply(compute_schedule_minimum, axis=1,
                                    args=(phases, wave_maps), xchar=xchar, **kwargs) #keep_assigned = True?
        if schedule_weight_col is not None:
            schedule_scores *= dfc[schedule_weight_col]
        min_score += schedule_scores.sum()

    for e in events:
        ephases = [ph for ph in phases if re.match(u.clean_regex(e), ph)]
        if phase_distrib_calc == 'none':
            ldp = 0
        elif phase_distrib_calc == 'max' and e in phase_maps:
            ldp = (phase_maps[e].apply(lambda s: s.nunique(), axis=0) > 1).sum()
        else:
            ldp = int(len(pools[e]) > 1)
        for i, ep in enumerate(ephases[:ldp]):
            islastphase = (i+1 == ldp)
            epdf = dfc.loc[dfc[ep].notna()]
            total_entries = epdf[e+'.Weight'].sum()
            seed_values = unique(epdf.groupby(e+'.Entry')[e+'.Value'].mean())
            for sv in seed_values:
                isvalue = epdf[e+'.Entry'].map(epdf.groupby(e+'.Entry')[e+'.Value'].mean() >= sv)
                vdf = epdf.loc[isvalue]
                vsr = vdf.groupby(e+'.Entry')[e+'.Weight'].sum()
                a4b = islastphase and (bracket_accounting == 'all' or (sv > 0 and bracket_accounting == 'ranked'))
                min_score += compute_distrib_minimum(vsr.values, len(ph_pools[ep]), a4b)
                for loc in locations:
                    pdf = epdf.loc[isvalue & u.notna_any(epdf, loc)]
                    places = pdf.groupby(loc).groups
                    for plc in places:
                        psr = pdf.loc[places[plc]].groupby(e+'.Entry')[e+'.Weight'].sum()
                        if psr.sum() < location_thold * total_entries:
                            min_score += compute_distrib_minimum(psr.values, len(ph_pools[ep]), a4b)
    return min_score


def compute_current_score(df, events, locations, pools, phase_maps=None,
                          bracket_accounting='none', pool_order=None,
                          skip_schedule=False, min_schedule_calc=False,
                          xchar=None, phase_distrib_calc='first',
                          schedule_weight_col=None, location_thold=1, **kwargs):
    # Note: bracket_accounting: {'all','ranked','none'}
    if phase_maps is None:
        phase_maps = {}
    if isinstance(pool_order, dict):
        pool_order.update({e: (lambda s: s) for e in events if e not in pool_order})
    elif pool_order is not None:
        pool_order = {e: pool_order for e in events}
    else:
        pool_order = {e: (lambda s: s) for e in events}

    dfc = df.copy()
    dfc = u.add_phase_columns(phase_maps, dfc, events, xchar)
    ph_pools = u.get_phase_pools(phase_maps, pools, events)
    phases = dfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    curr_score = 0.0
    if not skip_schedule:
        if min_schedule_calc:
            wave_maps = u.get_phase_wave_maps(phase_maps, pools, events)
            schedule_scores = dfc.apply(compute_schedule_minimum, axis=1, args=(phases, wave_maps),
                                        keep_assigned=True, xchar=xchar, **kwargs)
        else:
            schedule_scores = dfc.apply(compute_schedule_contribution, axis=1, args=(phases,), **kwargs)
        if schedule_weight_col is not None:
            schedule_scores *= dfc[schedule_weight_col]
        curr_score += schedule_scores.sum()

    for e in events:
        ephases = [ph for ph in phases if re.match(u.clean_regex(e), ph)]
        if phase_distrib_calc == 'none':
            ldp = 0
        elif phase_distrib_calc == 'max' and e in phase_maps:
            ldp = (phase_maps[e].apply(lambda s: s.nunique(), axis=0) > 1).sum()
        else:
            ldp = int(len(pools[e]) > 1)
        for i, ep in enumerate(ephases[:ldp]):
            islastphase = (i+1 == ldp)
            epdf = dfc.loc[dfc[ep].notna()]
            if isinstance(pool_order[e], Series):
                ordered_pools = pool_order[e].loc[ph_pools[ep]].tolist()
            elif isinstance(pool_order[e], dict):
                ordered_pools = [pool_order[e][pp] for pp in ph_pools[ep]]
            else:
                ordered_pools = [pool_order[e](pp) for pp in ph_pools[ep]]
            total_entries = epdf[e+'.Weight'].sum()
            seed_values = unique(epdf.groupby(e+'.Entry')[e+'.Value'].mean())
            for sv in seed_values:
                isvalue = epdf[e+'.Entry'].map(epdf.groupby(e+'.Entry')[e+'.Value'].mean() >= sv)
                vdf = epdf.loc[isvalue]
                vgp = vdf.groupby(e+'.Entry').agg({ep: 'first', e+'.Weight': 'sum'})
                vgp[ep] = vgp[ep].map(pool_order[e])
                vpc = vgp.groupby(ep)[e+'.Weight'].sum()
                a4b = islastphase and (bracket_accounting == 'all' or (sv > 0 and bracket_accounting == 'ranked'))
                curr_score += compute_distrib_contribution(vpc, ordered_pools, a4b)
                for loc in locations:
                    pdf = epdf.loc[isvalue & u.notna_any(epdf, loc)]
                    places = pdf.groupby(loc).groups
                    for plc in places:
                        pgp = pdf.loc[places[plc]].groupby(e+'.Entry').agg({ep: 'first',
                                                                            e+'.Weight': 'sum'})
                        pgp[ep] = pgp[ep].map(pool_order[e])
                        ppc = pgp.groupby(ep)[e+'.Weight'].sum()
                        if ppc.sum() < location_thold * total_entries:
                            curr_score += compute_distrib_contribution(ppc, ordered_pools, a4b)
    return curr_score


def compute_score_change(olddf, newdf, diffs, e, events, locations, pools, phase_maps=None,
                         bracket_accounting=None, pool_order=None, skip_schedule=False,
                         min_schedule_calc=False, xchar=None, phase_distrib_calc='first',
                         schedule_weight_col=None, location_thold=1, **kwargs):
    if phase_maps is None:
        phase_maps = {}
    if pool_order is None:
        pool_order = lambda s: s

    olddfc = olddf.copy()
    newdfc = newdf.copy()
    olddfc = u.add_phase_columns(phase_maps, olddfc, events, xchar)
    newdfc = u.add_phase_columns(phase_maps, newdfc, events, xchar)
    ph_pools = u.get_phase_pools(phase_maps, pools, events)
    phases = olddfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    members = newdfc.groupby(e+'.Entry').groups
    mixs = [members[d] for d in diffs]
    jxs = reduce(lambda a,b: a.append(b), mixs, Index([]))

    old_score = 0.0
    new_score = 0.0
    if not skip_schedule:
        if min_schedule_calc:
            wave_maps = u.get_phase_wave_maps(phase_maps, pools, events)
            old_sched_scores = olddfc.loc[jxs].apply(compute_schedule_minimum, axis=1, args=(phases, wave_maps),
                                                     keep_assigned=True, xchar=xchar, **kwargs)
            new_sched_scores = newdfc.loc[jxs].apply(compute_schedule_minimum, axis=1, args=(phases, wave_maps),
                                                     keep_assigned=True, xchar=xchar, **kwargs)
        else:
            old_sched_scores = olddfc.loc[jxs].apply(compute_schedule_contribution, axis=1, args=(phases,), **kwargs)
            new_sched_scores = newdfc.loc[jxs].apply(compute_schedule_contribution, axis=1, args=(phases,), **kwargs)
        if schedule_weight_col is not None:
            old_sched_scores *= olddfc.loc[jxs, schedule_weight_col]
            new_sched_scores *= newdfc.loc[jxs, schedule_weight_col]
        old_score += old_sched_scores.sum()
        new_score += new_sched_scores.sum()

    max_mean_value = max([olddfc.loc[members[d], e+'.Value'].mean() for d in diffs])
    ephases = [ph for ph in phases if re.match(u.clean_regex(e), ph)]
    if phase_distrib_calc == 'none':
        ldp = 0
    elif phase_distrib_calc == 'max' and e in phase_maps:
        ldp = (phase_maps[e].apply(lambda s: s.nunique(), axis=0) > 1).sum()
    else:
        ldp = int(len(pools[e]) > 1)
    for i, ep in enumerate(ephases[:ldp]):
        islastphase = (i+1 == ldp)
        oepdf = olddfc.loc[olddfc[ep].notna()]
        nepdf = newdfc.loc[newdfc[ep].notna()]
        if isinstance(pool_order, Series):
            ordered_pools = pool_order.loc[ph_pools[ep]].tolist()
        elif isinstance(pool_order, dict):
            ordered_pools = [pool_order[pp] for pp in ph_pools[ep]]
        else:
            ordered_pools = [pool_order(pp) for pp in ph_pools[ep]]
        total_entries = oepdf[e+'.Weight'].sum()
        seed_values = unique(oepdf.groupby(e+'.Entry')[e+'.Value'].mean())
        for sv in seed_values:
            if sv > max_mean_value:
                break
            oldisvalue = oepdf[e+'.Entry'].map(oepdf.groupby(e+'.Entry')[e+'.Value'].mean() >= sv)
            ovdf = oepdf.loc[oldisvalue]
            ovgp = ovdf.groupby(e+'.Entry').agg({ep: 'first', e+'.Weight': 'sum'})
            ovgp[ep] = ovgp[ep].map(pool_order)
            ovpc = ovgp.groupby(ep)[e+'.Weight'].sum()
            newisvalue = nepdf[e+'.Entry'].map(nepdf.groupby(e+'.Entry')[e+'.Value'].mean() >= sv)
            nvdf = nepdf.loc[newisvalue]
            nvgp = nvdf.groupby(e+'.Entry').agg({ep: 'first', e+'.Weight': 'sum'})
            nvgp[ep] = nvgp[ep].map(pool_order)
            nvpc = nvgp.groupby(ep)[e+'.Weight'].sum()
            a4b = islastphase and (bracket_accounting == 'all' or (sv > 0 and bracket_accounting == 'ranked'))
            old_score += compute_distrib_contribution(ovpc, ordered_pools, a4b)
            new_score += compute_distrib_contribution(nvpc, ordered_pools, a4b)
            for loc in locations:
                opdf = oepdf.loc[oldisvalue & u.notna_any(oepdf, loc)]
                npdf = nepdf.loc[newisvalue & u.notna_any(nepdf, loc)]
                places = opdf.groupby(loc).groups
                if isinstance(loc, (list,tuple)):
                    jps = olddfc.loc[jxs, loc].apply(tuple, axis=1).unique().tolist()
                else:
                    jps = olddfc.loc[jxs, loc].unique().tolist()
                for plc in jps:
                    if plc in places:
                        opgp = opdf.loc[places[plc]].groupby(e+'.Entry').agg({ep: 'first',
                                                                              e+'.Weight': 'sum'})
                        opgp[ep] = opgp[ep].map(pool_order)
                        oppc = opgp.groupby(ep)[e+'.Weight'].sum()
                        npgp = npdf.loc[places[plc]].groupby(e+'.Entry').agg({ep: 'first',
                                                                              e+'.Weight': 'sum'})
                        npgp[ep] = npgp[ep].map(pool_order)
                        nppc = npgp.groupby(ep)[e+'.Weight'].sum()
                        if oppc.sum() < location_thold * total_entries:
                            old_score += compute_distrib_contribution(oppc, ordered_pools, a4b)
                            new_score += compute_distrib_contribution(nppc, ordered_pools, a4b)
    return (new_score-old_score)
