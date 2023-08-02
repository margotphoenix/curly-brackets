
from math import log2, ceil

from PyPDF2 import PdfFileWriter

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


def _auto_advance_entrants(entrants, names, format):
    rounds = []
    for entrs, nms in zip(entrants, names):
        bsize = len(nms)
        ts = 2**ceil(log2(len(entrs)))
        tsh = 2**ceil(log2(len(entrs)/1.5))
        if tsh == ts: 
            rnds = {
                'WR1': nms,
                'WR2': seeds_to_sequential(
                    entrs[:(len(nms)-len(entrs))],
                    size=bsize//2),
                }
            rnds['LR1'] = [
                nms[2*i+1] if rnds['WR2'][i] == nms[2*i] else ''
                for i in range(bsize//2)]
            rnds['LR2'] = [
                '' if i % 2 == 0 else rnds['LR1'][i]
                for i in range(bsize//2)]
        else:
            rnds = {
                'WR1': [
                    nms[i] for i in range(len(nms)) if (i//2)%2 == 1],
                'WR2': seeds_to_sequential(
                    entrs[:(len(nms)-len(entrs))],
                    size=bsize//2)
            }
            rnds['LR1'] = [
                nms[2*i+1] if rnds['WR2'][i] == nms[2*i] else ''
                for i in range(bsize//2)]
            rnds['LR1'] = [
                '' if i % 2 == 0 else rnds['LR1'][i]
                for i in range(bsize//2)]

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
        print(nms)
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
            print(nent)
            tf = TemplateLookup.search(format=format,
                                       n_entrants=nent, **vkwargs)
        print(tf)

        template_files.append(tf)
        if tf not in template_brackets:
            template_brackets[tf] = TemplateLookup.get(tf)
            template_brackets[tf].create()

        template_brackets[tf].draw_page(nms, **vkwargs)
        template_brackets[tf].next_page()

    for tf in template_brackets:
        template_brackets[tf].save()

    document = PdfFileWriter()
    template_pages = {tf: template_brackets[tf].merge_pages()
                      for tf in template_brackets}
    for tf in template_files:
        merged_page = next(template_pages[tf])
        document.addPage(merged_page)

    with open(filename, 'wb') as f:
        document.write(f)


def print_initial_bracket(filename, entrants, format='double-elimination',
                          n_advance=0, name_order='seed', bracket_size=None,
                          entrants_textgray=0, byes=None, byes_textgray=0.85,
                          auto_advance=False, **kwargs):
    """ Make bracket pdf where all players start in winners

    Parameters
    ----------
    filename : str
    entrants :
    """
    if not isinstance(entrants[0], (tuple, list)):
        entrants = [entrants]
    if not byes:
        byes = 'none'
    format = get_format(format)

    total = [str(len(entrs)) for entrs in entrants]

    if format[0] in ['d', 's'] and name_order != 'sequential':
        if byes in ['none', 'block']:
            bye_fill = (None if byes == 'block' else '')
            names = [seeds_to_sequential(
                entrs, size=bracket_size, fill=bye_fill
                ) for entrs in entrants]
            names_textgray = entrants_textgray

            if auto_advance:
                names = _auto_advance_entrants(
                    entrants, names, format
                )
        else:
            bye_fill = ('Bye {:d}' if byes == 'number' else 'Bye')
            names = []
            names_textgray = []
            for entrs in entrants:
                names.append(seeds_to_sequential(
                    entrs, size=bracket_size, fill=bye_fill
                ))
                names_textgray.append(seeds_to_sequential(
                    [entrants_textgray for _ in entrs],
                    size=bracket_size, fill=byes_textgray
                ))

            if auto_advance:
                names = _auto_advance_entrants(
                    entrants, names, format
                )
                names_textgray = {'WR1': names_textgray, 
                                  'WR2': entrants_textgray}  # This won't work for 24
                if format[0] == 'd':
                    names_textgray.update({'LR1': byes_textgray, 
                                           'LR2': byes_textgray})
    else:
        names = entrants
        names_textgray = entrants_textgray

    if bracket_size:
        kwargs['bracket_size'] = bracket_size
    print_bracket(filename, names, format, n_advance=n_advance,
                  total=total, names_textgray=names_textgray, **kwargs)


def print_continued_bracket(filename, in_winners, in_losers,
                            format='double-elimination', n_advance=0,
                            winners_arrow='\u226b', losers_arrow='\u226a', 
                            pre_advance=False, **kwargs):
    """ Make bracket pdf where some players start in losers

    Parameters
    ----------
    filename : str
    in_winners :
    in_losers :
    """
    if not isinstance(in_winners[0], (tuple, list)):
        in_winners = [in_winners]
    if not isinstance(in_losers[0], (tuple, list)):
        in_losers = [in_losers]
    if len(in_winners) != len(in_losers):
        raise ValueError('Winners and losers name lists must be same length')

    format = get_format(format)
    if format != 'double-elimination':
        raise ValueError(f'Cannot create continued bracket with'
                         f'{format} format')

    names = []
    names_vkwargs = []
    for win, los in zip(in_winners, in_losers):
        nms_vkw = {'n_in_winners': len(win),
                   'n_in_losers': len(los),
                   'total': str(len(win)+len(los))}

        if pre_advance:
            nms = {
                'WR1': win,
                'LR1': los
            }
        else:
            if winners_arrow:
                win = [f'{n} {winners_arrow}' for n in win]
            if losers_arrow:
                los = [f'{losers_arrow} {n}' for n in los]

            nms = []
            if len(los) == 2*len(win):
                for i in range(len(win)):
                    nms += [win[i], los[2*i], '', los[2*i+1]]
            elif len(los) == len(win):
                for i in range(len(win)):
                    nms += [win[i], los[i]]
            else:
                raise ValueError('Incompatible lengths for winners and losers'
                                'name lists')

            nms_aln = []
            for i in range(len(los)):
                nms_aln += ['right', 'left']
            nms_vkw.update(names_alignment=nms_aln)

        names.append(nms)
        names_vkwargs.append(nms_vkw)

    names_kwargs = collapse_kwargs(names_vkwargs)
    print_bracket(filename, names, format, n_advance=n_advance,
                  **kwargs, **names_kwargs)
