import re
from functools import partial

from pandas import Series, DataFrame, isna
from numpy import unique

from . import compute as c
from . import utilities as u


def find_schedule_conflicts(df, events, xchar=None, phase_transitions=None, pools=None):
    if phase_transitions is None:
        phase_transitions = {}
    phase_maps = u.maps_from_transitions(phase_transitions, pools)

    dfc = df.copy()
    dfc = u.add_phase_columns(phase_maps, dfc, events, xchar)
    phases = dfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    sc_ix = []
    for ix, row in dfc.iterrows():
        phases_ent = row[phases].dropna()
        if len(phases_ent) > 0:
            block_vc = u.count_blocks(phases_ent, xchar)
            if (block_vc > 1).any():
                sc_ix.append(ix)
    return sc_ix


def find_external_conflicts(df, events, external=None, xchar=None,
                            phase_transitions=None, pools=None, splitchar=None):
    if external is None:
        return []
    if phase_transitions is None:
        phase_transitions = {}
    phase_maps = u.maps_from_transitions(phase_transitions, pools)
    splitter = list if splitchar is None else partial(str.split, sep=splitchar)

    dfc = df.copy()
    dfc = u.add_phase_columns(phase_maps, df, events, xchar)
    phases = dfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    ex_ix = []
    for ix, row in dfc.iterrows():
        if isna(row[external]):
            continue
        phases_ent = row[phases].dropna()
        if len(phases_ent) > 0:
            block_vc = u.count_blocks(phases_ent, xchar)
            if (block_vc.reindex(splitter(row[external])).fillna(0) > 0).any():
                ex_ix.append(ix)
    return ex_ix


def find_suboptimal_schedules(df, events, pools=None, phase_transitions=None, xchar=None, **kwargs):
    if phase_transitions is None:
        phase_transitions = {}
    phase_maps = u.maps_from_transitions(phase_transitions, pools)
    if pools is None:
        pools = {e: df[e].dropna().unique() for e in events}

    dfc = df.copy()
    dfc = u.add_phase_columns(phase_maps, df, events, xchar)
    wave_maps = u.get_phase_wave_maps(phase_maps, pools, events)
    phases = dfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    min_scores = dfc.apply(c.compute_schedule_minimum, axis=1, args=(phases, wave_maps),
                           keep_assigned=False, xchar=xchar, **kwargs)
    curr_scores = dfc.apply(c.compute_schedule_minimum, axis=1, args=(phases, wave_maps),
                            keep_assigned=True, xchar=xchar, **kwargs)
    so_ix = dfc.loc[curr_scores > min_scores].index.tolist()
    return so_ix


def find_suboptimal_distributions(df, events, locations, pools, pk=None, phase_transitions=None,
                                  include_seeds=False, bracket_accounting='none', pool_order=None,
                                  phase_distrib_calc='first', location_thold=1, diff_th=1e-7, return_costs=False):
    if phase_transitions is None:
        phase_transitions = {}
    phase_maps = u.maps_from_transitions(phase_transitions, pools)
    if isinstance(pool_order, dict):
        pool_order.update({e: (lambda s: s) for e in events if e not in pool_order})
    elif pool_order is not None:
        pool_order = {e: pool_order for e in events}
    else:
        pool_order = {e: (lambda s: s) for e in events}


    dfc = df.copy()
    dfc = u.add_entry_columns(dfc, events, pk)
    dfc = u.add_phase_columns(phase_maps, dfc, events)
    ph_pools = u.get_phase_pools(phase_maps, pools, events)
    phases = dfc.filter(regex=r'[.]{2}[1-9][0-9]*$').columns.tolist()

    so_tuples = []
    score_costs = []
    for e in events:
        ephases = [ph for ph in phases if re.match(u.clean_regex(e), ph)]
        if phase_distrib_calc == 'none':
            ldp = 0
        elif phase_distrib_calc == 'max' and e in phase_maps:
            ldp = (phase_maps[e].apply(lambda s: s.nunique(), axis=0) > 1).sum()
        else:
            ldp = int(len(pools[e]) > 1)
        for i,ep in enumerate(ephases[:ldp]):
            islastphase = (i+1 == ldp)
            ep_tpl = (e,) if len(ephases) == 1 else (e,i+1)
            epdf = dfc.loc[dfc[ep].notna()]
            if isinstance(pool_order[e], Series):
                ordered_pools = pool_order[e].loc[ph_pools[ep]].tolist()
            elif isinstance(pool_order[e], dict):
                ordered_pools = [pool_order[e][pp] for pp in ph_pools[ep]]
            else:
                ordered_pools = [pool_order[e](pp) for pp in ph_pools[ep]]
            total_entries = epdf[e+'.Weight'].sum()
            if include_seeds and e+'.Value' in epdf.columns:
                seed_values = unique(epdf.groupby(e+'.Entry')[e+'.Value'].mean())
            else:
                seed_values = [0]
            for sv in seed_values:
                if e+'.Value' in epdf.columns:
                    isvalue = epdf[e+'.Entry'].map(epdf.groupby(e+'.Entry')[e+'.Value'].mean() >= sv)
                else:
                    isvalue = epdf[e+'.Entry'].map(lambda s: True)
                vdf = epdf.loc[isvalue]
                vsr = vdf.groupby(e+'.Entry')[e+'.Weight'].sum()
                vgp = vdf.groupby(e+'.Entry').agg({ep: 'first', e+'.Weight': 'sum'})
                vgp[ep] = vgp[ep].map(pool_order[e])
                vpc = vgp.groupby(ep)[e+'.Weight'].sum()
                a4b = islastphase and (bracket_accounting == 'all' or (sv > 0 and bracket_accounting == 'ranked'))
                min_contrib = c.compute_distrib_minimum(vsr.values, len(ph_pools[ep]), a4b)
                curr_contrib = c.compute_distrib_contribution(vpc, ordered_pools, a4b)
                if curr_contrib - min_contrib > diff_th:
                    slp_tpl = (e+'.Value',sv) if sv > 0 else ()
                    so_tuples.append(ep_tpl + slp_tpl)
                    score_costs.append(curr_contrib - min_contrib)
                for loc in locations:
                    pdf = epdf.loc[isvalue & u.notna_any(epdf,loc)]
                    places = pdf.groupby(loc).groups
                    for plc in places:
                        psr = pdf.loc[places[plc]].groupby(e+'.Entry')[e+'.Weight'].sum()
                        pgp = pdf.loc[places[plc]].groupby(e+'.Entry').agg({ep: 'first',
                                                                            e+'.Weight': 'sum'})
                        pgp[ep] = pgp[ep].map(pool_order[e])
                        ppc = pgp.groupby(ep)[e+'.Weight'].sum()
                        if psr.sum() < location_thold*total_entries:
                            min_contrib = c.compute_distrib_minimum(psr.values, len(ph_pools[ep]), a4b)
                            curr_contrib = c.compute_distrib_contribution(ppc, ordered_pools, a4b)
                            if curr_contrib - min_contrib > diff_th:
                                slp_tpl = ((e+'.Value',loc),(sv,plc)) if sv > 0 else (loc,plc)
                                so_tuples.append(ep_tpl + slp_tpl)
                                score_costs.append(curr_contrib - min_contrib)
    if return_costs:
        return so_tuples, score_costs
    else:
        return so_tuples


def get_distribution(df, event, location, place, pk=None, phase=1,
                     phase_transition=None, pools=None, pool_order=None):
    if pools is not None and not isinstance(pools, dict):
        pools = {event: pools}
    if phase_transition is None:
        phase_transition = {}
    elif not isinstance(phase_transition, dict):
        phase_transition = {event: phase_transition}
    phase_maps = u.maps_from_transitions(phase_transition, pools)
    if pool_order is None:
        pool_order = (lambda s: s)
    elif isinstance(pool_order, dict) and event in pool_order:
        pool_order = pool_order[event]

    dfc = df.copy()
    dfc = u.add_entry_columns(dfc, [event], pk)
    dfc = u.add_phase_columns(phase_maps, dfc, [event])

    event_phase = event+'..'+str(phase)

    epdf = dfc.loc[dfc[event_phase].notna()]
    ph_pools = epdf[event_phase].unique().tolist()
    if isinstance(pool_order, Series):
        ordered_pools = pool_order.loc[ph_pools].tolist()
    elif isinstance(pool_order, dict):
        ordered_pools = [pool_order[pp] for pp in ph_pools]
    else:
        ordered_pools = [pool_order(pp) for pp in ph_pools]
    pdf = epdf.loc[u.notna_any(epdf,location)]
    places = pdf.groupby(location).groups
    pgp = pdf.loc[places[place]].groupby(event+'.Entry').agg({event_phase: 'first',
                                                              event+'.Weight': 'sum'})
    pgp[event_phase] = pgp[event_phase].map(pool_order)
    ppc = pgp.groupby(event_phase)[event+'.Weight'].sum()
    dist = Series(0.0, index=ordered_pools)
    dist = dist.add(ppc, fill_value=0.0)
    return dist.sort_index()
