
from math import log2, ceil

from PyPDF2 import PdfWriter

from curlybrackets.pdf.brackets import TemplateLookup
from curlybrackets.pdf.utilities import expand_kwargs, collapse_kwargs

from curlybrackets.utilities import seeds_to_sequential


def get_format(format):
    if format.lower().startswith('d'):
        return 'double-elimination'
    elif format.lower().startswith('s'):
        return 'single-elimination'
    elif format.lower().startswith('r'):
        return 'round-robin'
    else:
        raise TypeError(f'Invalid tournament format: {format}')


def _auto_advance_entrants(entrants, names, 
                           bracket_size, format):
    rounds = []
    for entrs, nms, bsz in zip(entrants, names, bracket_size):
        if bsz is None:
            ts = 2**ceil(log2(len(entrs)))
            tsh = 2**ceil(log2(len(entrs)/1.5))
        else:
            ts = 2**ceil(log2(bsz))
            tsh = 2**ceil(log2(bsz/1.5))
        if tsh == ts: 
            rnds = {
                'WR1': nms,
                'WR2': seeds_to_sequential(
                    entrs[:(len(nms)-len(entrs))],
                    size=len(nms)//2),
                }
            rnds['LR1'] = [
                nms[2*i+1] if rnds['WR2'][i] == nms[2*i] else ''
                for i in range(len(nms)//2)]
            rnds['LR2'] = [
                '' if i % 2 == 0 else rnds['LR1'][i]
                for i in range(len(nms)//2)]
        else:
            rnds = {
                'WR1': [
                    nms[i] for i in range(len(nms)) if (i//2)%2 == 1],
                'WR2': seeds_to_sequential(
                    entrs[:(len(nms)-len(entrs))],
                    size=len(nms)//2)
            }
            rnds['LR1'] = [
                nms[2*i+1] if rnds['WR2'][i] == nms[2*i] else ''
                for i in range(len(nms)//2)]
            rnds['LR1'] = [
                '' if i % 2 == 0 else rnds['LR1'][i]
                for i in range(len(nms)//2)]

        rounds.append(rnds)
    return rounds


def print_bracket(filename, names, format, **kwargs):
    """ Make bracket pdf

    Parameters
    ----------
    filename : str
    names :
    """
    if not isinstance(names[0], (tuple, list, dict)):
        names = [names]
    format = get_format(format)

    var_kwargs = expand_kwargs(len(names), **kwargs)

    template_files = []
    template_brackets = {}
    for nms, vkwargs in zip(names, var_kwargs):
        try:
            tf = TemplateLookup.search(format=format, **vkwargs)
        except KeyError:
            if isinstance(nms, dict):
                if len(nms['WR1']) == len(nms['WR2']):
                    nent = len(nms['WR1']) + len(nms['WR2'])//2
                else:
                    nent = len(nms['WR1'])
            else:
                nent = len(nms)
            tf = TemplateLookup.search(format=format,
                                       n_entrants=nent, **vkwargs)
        # print(tf)

        template_files.append(tf)
        if tf not in template_brackets:
            template_brackets[tf] = TemplateLookup.get(tf)
            template_brackets[tf].create()

        template_brackets[tf].draw_page(nms, **vkwargs)
        template_brackets[tf].next_page()

    for tf in template_brackets:
        template_brackets[tf].save()

    document = PdfWriter()
    template_pages = {tf: template_brackets[tf].merge_pages()
                      for tf in template_brackets}
    for tf in template_files:
        merged_page = next(template_pages[tf])
        document.add_page(merged_page)

    with open(filename, 'wb') as f:
        document.write(f)


def print_initial_bracket(filename, entrants, format='double-elimination',
                          n_advance=0, name_order='seed', bracket_size=None,
                          entrants_textgray=0, byes=None, 
                          byes_gray=0.5, byes_alpha=None,
                          auto_advance=False, **kwargs):
    """ Make bracket pdf where all players start in winners

    Parameters
    ----------
    filename : str
    entrants :
    """
    if not isinstance(entrants[0], (tuple, list)):
        entrants = [entrants]
    if bracket_size is not None:
        kwargs['bracket_size'] = bracket_size
    if not isinstance(bracket_size, (tuple, list)):
        bracket_size = [bracket_size] * len(entrants)
    if not byes:
        byes = 'none'
    format = get_format(format)

    total = [str(len(entrs)) for entrs in entrants]

    if format[0] in ['d', 's'] and name_order != 'sequential':
        if byes in ['none', 'block']:
            bye_fill = (None if byes == 'block' else '')
            names = [seeds_to_sequential(
                entrs, size=bsize, fill=bye_fill
                ) for entrs, bsize in zip(entrants, bracket_size)]
            names_textgray = entrants_textgray

            if auto_advance:
                names = _auto_advance_entrants(
                    entrants, names, bracket_size, format
                )

            kwargs['names_backgray'] = byes_gray
            kwargs['names_backalpha'] = byes_alpha
        else:
            bye_fill = ('Bye {:d}' if byes == 'number' else 'Bye')
            names = []
            names_textgray = []
            for entrs, bsize in zip(entrants, bracket_size):
                names.append(seeds_to_sequential(
                    entrs, size=bsize, fill=bye_fill
                ))
                names_textgray.append(seeds_to_sequential(
                    [entrants_textgray for _ in entrs],
                    size=bsize, fill=byes_gray
                ))

            if auto_advance:
                names = _auto_advance_entrants(
                    entrants, names, bracket_size, format
                )
                names_textgray = {'WR1': names_textgray, 
                                  'WR2': entrants_textgray}  # This won't work for 24
                if format[0] == 'd':
                    names_textgray.update({'LR1': byes_gray, 
                                           'LR2': byes_gray})
            
            kwargs['names_textgray'] = names_textgray
    else:
        names = entrants
        if 'names_textgray' not in kwargs:
            kwargs['names_textgray'] = entrants_textgray

    print_bracket(filename, names, format, n_advance=n_advance,
                  total=total, names_textgray=names_textgray, **kwargs)


def print_continued_bracket(filename, winners_entrants=None, losers_entrants=None,
                            winners_origins=None, losers_origins=None,
                            format='double-elimination', n_advance=0,
                            # winners_arrow='\u226b', losers_arrow='\u226a', 
                            **kwargs):
    """ Make bracket pdf where some players start in losers

    Parameters
    ----------
    filename : str
    winners_entrants :
    losers_entrants :
    """
    if (winners_entrants is None and losers_entrants is None 
        and winners_origins is None and losers_origins is None):
        raise ValueError('Must specify either names or origins')
        
    if winners_entrants is not None and not isinstance(winners_entrants[0], (tuple, list)):
        winners_entrants = [winners_entrants]
    if losers_entrants is not None and not isinstance(losers_entrants[0], (tuple, list)):
        losers_entrants = [losers_entrants]
    if (winners_entrants is not None and losers_entrants is not None 
        and len(winners_entrants) != len(losers_entrants)):
        raise ValueError('Winners and losers entrant lists must be same length')
    if winners_origins is not None and not isinstance(winners_origins[0], (tuple, list)):
        winners_origins = [winners_origins]
    if losers_origins is not None and not isinstance(losers_origins[0], (tuple, list)):
        losers_origins = [losers_origins]
    if (winners_origins is not None and losers_origins is not None 
        and len(winners_origins) != len(losers_origins)):
        raise ValueError('Winners and losers origin lists must be same length')

    if (winners_entrants is not None and losers_entrants is not None 
        and winners_origins is None and losers_origins is None):
        winners_origins = [None] * len(winners_entrants)
        losers_origins = [None] * len(losers_entrants)
    elif (winners_entrants is None and losers_entrants is None 
          and winners_origins is not None and losers_origins is not None):
        winners_entrants = [None] * len(winners_origins)
        losers_entrants = [None] * len(losers_origins)
    
    format = get_format(format)
    if format != 'double-elimination':
        raise ValueError(f'Cannot create continued bracket with'
                         f'{format} format')

    names = []
    names_vkwargs = []
    names_iter = zip(winners_entrants, losers_entrants, winners_origins, losers_origins)
    for win_e, los_e, win_o, los_o in names_iter:
        n_in_winners = max(len(win_e or []), len(win_o or []))
        n_in_losers = max(len(los_e or []), len(los_o or []))
        nms_vkw = {'n_in_winners': n_in_winners,
                   'n_in_losers': n_in_losers,
                   'total': str(n_in_winners + n_in_losers)}
        
        nms = {}
        if win_e is not None:
            nms['WR1'] = win_e
        if los_e is not None:
            nms['LR1'] = los_e
        if win_o is not None:
            nms['WR0'] = win_o
        if los_o is not None:
            nms['LR0'] = los_o

        names.append(nms)
        names_vkwargs.append(nms_vkw)

    names_kwargs = collapse_kwargs(names_vkwargs)
    print_bracket(filename, names, format, n_advance=n_advance,
                  **kwargs, **names_kwargs)
