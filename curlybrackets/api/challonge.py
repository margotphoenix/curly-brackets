from dateutil import parser

import challonge

from ..utilities import seed_order


NEW_TOURNAMENT_DEFAULTS = {'tournament_type': 'double elimination',
                           'open_signup': False,
                           'sequential_pairings': True,
                           'hide_seeds': True,
                           'quick_advance': True,
                           'accept_attachments': True,
                           'allow_participant_match_reporting': False,
                           'notify_users_when_matches_open': False,
                           'notify_users_when_the_tournament_ends': False}


set_credentials = challonge.set_credentials


def make_challonge(players, name, url, start=True, miscs=None, destroy_if_existing=True, **kwargs):
    kwargs = {**NEW_TOURNAMENT_DEFAULTS, **kwargs}

    if miscs is not None and len(miscs) != len(players):
        raise ValueError('Miscelaneous list must be same length as player name list')

    try:
        t = challonge.tournaments.create(name, url, **kwargs)
    except challonge.api.ChallongeException:
        if 'subdomain' in kwargs:
            urlfmt = kwargs['subdomain']+'-'+url
        else:
            urlfmt = url
        if destroy_if_existing:
            challonge.tournaments.destroy(urlfmt)
            t = challonge.tournaments.create(name, url, **kwargs)
        else:
            t = challonge.tournaments.show(urlfmt)
            if t['state'] != 'pending':
                challonge.tournaments.reset(urlfmt)
            ps = challonge.participants.index(urlfmt)
            for p in ps:
                challonge.participants.destroy(urlfmt,p['id'])
            challonge.tournaments.update(urlfmt, name=name, **kwargs)
            t = challonge.tournaments.show(urlfmt)

    order = seed_order(len(players))
    np = sum(map(lambda s: s!='', players))
    if kwargs['sequential_pairings'] and len(order) > len(players):
        raise ValueError('Number of players must be a power of 2 in order to use sequential pairings')

    bye_num = 0
    player_names = []
    for i,player in enumerate(players):
        if player == '':
            if kwargs['sequential_pairings']:
                bye_num = order[i]-np
            else:
                bye_num += 1
            player_names.append('[[Bye '+str(bye_num)+']]')
        else:
            player_names.append(player)

    if miscs:
        challonge.participants.bulk_add(t['id'], player_names, misc=miscs)
    else:
        challonge.participants.bulk_add(t['id'], player_names)

    if start:
        challonge.tournaments.start(t['id'])

    return t['id']


def get_urls_from_subdomain(org):
    ts = challonge.tournaments.index(subdomain=org)
    urls = [t['url'] for t in ts]
    return urls


def update_time(tid, start_at):
    challonge.tournaments.reset(tid)
    challonge.tournaments.update(tid, start_at=start_at)
    challonge.tournaments.start(tid)


def free_advance(tid):
    t = challonge.tournaments.show(tid)

    if t['state'] == 'pending':
        challonge.tournaments.start(t['id'])

    autocount = 1
    while autocount > 0:
        autocount = 0
        ms = challonge.matches.index(t['id'])
        for m in ms:
            if m['state'] != 'open':
                continue
            p1 = challonge.participants.show(t['id'], m['player1_id'])
            p2 = challonge.participants.show(t['id'], m['player2_id'])
            if p2['name'].startswith('[[Bye '):
                challonge.matches.update(t['id'], m['id'], winner_id=p1['id'], scores_csv="1-0")
                autocount += 1
            elif p1['name'].startswith('[[Bye '):
                challonge.matches.update(t['id'], m['id'], winner_id=p2['id'], scores_csv="0-1")
                autocount += 1


def get_participant_list(tid, misc=False):
    part_list = []
    misc_list = []
    ps = challonge.participants.index(tid)
    for p in ps:
        if p['name'].startswith('[[Bye '):
            part_list.append('')
            misc_list.append('')
        else:
            part_list.append(p['name'].encode('utf-8'))
            misc_list.append(p['misc'])
    if misc:
        return part_list, misc_list
    else:
        return part_list


def get_participant_misc(tid):
    misc_list = []
    ps = challonge.participants.index(tid)
    for p in ps:
        misc_list.append(p['misc'])
    return misc_list


def get_participant_count(tid):
    t = challonge.tournaments.show(tid)
    return t['participants_count']


def expand_bracket(tid, bye_char='X'):
    t = challonge.tournaments.show(tid)
    started = (t['state'] == 'underway')
    if started:
        challonge.tournaments.reset(t['id'])

    n = t['participants_count']
    order = seed_order(n)
    m = len(order)

    if m > n:
        if t['sequential_pairings']:
            raise ValueError('Number of players must be a power of 2 in order to use sequential pairings')
        else:
            for j in range(m-n):
                bye_name = '[[Bye ' + bye_char + str(j+1) + ']]'
                bye_seed = n+j+1
                challonge.participants.create(t['id'], name=bye_name, seed=bye_seed)

    for i in range(m):
        if t['sequential_pairings']:
            bye_name = '[[Bye ' + bye_char + str(m+1-order[i]) + ']]'
            bye_seed = 2*(i+1)
        else:
            bye_name = '[[Bye ' + bye_char + str(m-n+i+1) + ']]'
            bye_seed = m+i+1
        challonge.participants.create(t['id'], name=bye_name, seed=bye_seed)

    if started:
        challonge.tournaments.start(t['id'])


def advancement_bracket_setup(tid, max_winners_round=1, max_losers_round=0):
    t = challonge.tournaments.show(tid)
    if t['state'] == 'pending':
        challonge.tournaments.start(t['id'])

    matches = challonge.matches.index(t['id'])
    #pc = t['participants_count']
    for m in matches:
        if m['round'] <= max_winners_round and m['round'] >= -abs(max_losers_round):
            challonge.matches.update(t['id'], m['id'], winner_id=m['player1-id'], scores_csv="1-0")
