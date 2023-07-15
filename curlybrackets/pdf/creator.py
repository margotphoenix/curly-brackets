
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


def print_bracket(filename, names, format, **kwargs):
    """ Make bracket pdf

    Parameters
    ----------
    filename : str
    names :
    """
    if not isinstance(names[0], (tuple, list)):
        names = [names]
    format = get_format(format)

    var_kwargs = expand_kwargs(len(names), **kwargs)

    template_files = []
    template_brackets = {}
    for nms, vkwargs in zip(names, var_kwargs):
        try:
            tf = TemplateLookup.search(format=format, **vkwargs)
        except KeyError:
            tf = TemplateLookup.search(format=format,
                                       n_entrants=len(nms), **vkwargs)

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
                          byes=None, entrants_textgray=0, byes_textgray=0.85,
                          **kwargs):
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
        if byes == 'none':
            names = [seeds_to_sequential(entrs, size=bracket_size)
                     for entrs in entrants]
            names_textgray = entrants_textgray
        else:
            if byes == 'number':
                names_fill = 'Bye {:d}'.format
            else:
                names_fill = 'Bye'
            names = []
            names_textgray = []
            for entrs in entrants:
                names.append(seeds_to_sequential(
                    entrs, size=bracket_size, fill=names_fill
                ))
                names_textgray.append(seeds_to_sequential(
                    [entrants_textgray for _ in entrs],
                    size=bracket_size, fill=byes_textgray
                ))
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
                            name_order='sequential', **kwargs):
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

    if name_order != 'sequential':
        raise NotImplementedError('Names must be in sequential order'
                                  'for continued bracket')

    names = []
    names_vkwargs = []
    for win, los in zip(in_winners, in_losers):
        nms_vkw = {'n_in_winners': len(win),
                   'n_in_losers': len(los),
                   'total': str(len(win)+len(los))}

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
