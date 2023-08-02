
import io
# from functools import partial, wraps
from importlib.resources import open_binary, open_text
import json
import warnings

from reportlab.pdfgen.canvas import Canvas

from PyPDF2 import PdfFileReader

from curlybrackets.pdf import templates
from curlybrackets.pdf.elements import (TextFieldElement,
                                        TextListElement,
                                        SlotListElement,
                                        ParagraphElement,
                                        ItemListElement,
                                        ImageElement)
from curlybrackets.pdf.pages import Page
from curlybrackets.pdf.fonts import DEFAULT_FONT, BASE_FONT
from curlybrackets.pdf.utilities import (expand_kwargs,
                                         collapse_kwargs,
                                         ProgressionFormatter, 
                                         NBSP, ENDA)


class Template:
    def __init__(self, template_file, format,
                 bracket_size, page, elements, **kwargs):
        self.template_file = template_file
        self.format = format
        self.bracket_size = bracket_size
        self.page = Page(**page)

        self.elements = ['names']
        names = kwargs.get('names')
        if isinstance(names, dict):
            self.names = {
                k: self.build_element('slotlist', **names[k])
                for k in names 
            }
        else: 
            self.names = [
                self.build_element('textlist', max_lines=bracket_size, **n) 
                for n in names
            ]
            self.elements.append('names')

        for e in elements:
            if e in ['names']:
                continue
            element_props = kwargs.pop(e)
            if isinstance(element_props, dict):
                element = self.build_element(e, **element_props)
            else:
                element = [self.build_element(e, **ep)
                           for ep in element_props]
            setattr(self, e, element)
            self.elements.append(e)

        self.meta = kwargs

    @staticmethod
    def build_element(element_name, **element_props):
        if element_name in ['slotlist']:
            base_class = SlotListElement
            element_defaults = {'fontname': DEFAULT_FONT, 'min_hscale': 60}
        elif element_name in ['textlist']:
            base_class = TextListElement
            element_defaults = {'fontname': DEFAULT_FONT, 'min_hscale': 60}
        elif element_name in ['event', 'label']:
            base_class = TextFieldElement
            element_defaults = {'fontname': BASE_FONT, 'min_hscale': 90}
        elif element_name in ['pool', 'date', 'total']:
            base_class = TextFieldElement
            element_defaults = {'fontname': BASE_FONT,
                                'alignment': 'center',
                                'min_hscale': 90}
        elif element_name in ['judge']:
            base_class = TextFieldElement
            element_defaults = {'fontname': DEFAULT_FONT, 'min_hscale': 90}
        elif element_name in ['progressions']:
            # if element_props.get('type') == 'list':
            #     base_class = ItemListElement
            # else:
            base_class = ParagraphElement
            element_defaults = {'fontname': BASE_FONT, 'valign': 'MIDDLE'}
        elif element_name in ['notes']:
            base_class = ItemListElement
            element_defaults = {'fontname': DEFAULT_FONT, 'bullet': ENDA}
        elif element_name in ['image']:
            base_class = ImageElement
            element_defaults = {}
        else:
            raise ValueError(f'Unrecognized element name: {element_name}')

        element_params = {**element_defaults, **element_props}
        return base_class(**element_params)

    def create(self):
        self.overlay_packet = io.BytesIO()
        self.canvas = Canvas(self.overlay_packet,
                             pagesize=self.page.size,
                             initialFontName=DEFAULT_FONT)

    def draw_names(self, names, **kwargs):
        if isinstance(self.names, dict): 
            if not isinstance(names, dict):
                names = {'WR1': names}
            for round in names:
                name_element = self.names[round]
                name_element.draw(self.canvas, names[round], **kwargs)
        else:
            for name_element in self.names:
                name_element.draw(self.canvas, names, **kwargs)

    def draw_progressions(self, progressions, format_string=None, **kwargs):
        if format_string is None:
            warnings.warn('Progressions skipped, must specify format_string')
            return
        for element in self.progressions:
            if element.type == 'rr':
                fmt_str = '{0:O} place advances to'.replace(' ', NBSP)
                fmt_str += ' ' + format_string
                prog_text = []
                for s in element.seeds:
                    if s in progressions:
                        text = ProgressionFormatter().format(fmt_str, s,
                                                             **progressions[s])
                        prog_text.append(text)
                prog_text = '<br/>'.join(prog_text)
            else:
                if len(element.seeds) > 1:
                    fmt_str = 'Players advance to'.replace(' ', NBSP)
                else:
                    fmt_str = 'Player advances to'.replace(' ', NBSP)
                fmt_str += ' ' + format_string
                prog = collapse_kwargs([progressions[s] for s in element.seeds])
                prog_text = ProgressionFormatter().format(fmt_str, **prog)
            element.draw(self.canvas, prog_text, **kwargs)

    def draw_element(self, element_name, element_value, **kwargs):
        if not hasattr(self, element_name):
            raise AttributeError(f'Template does not have attribute: '
                                 f'{element_name}')
        if element_name == 'names':
            self.draw_names(element_value, **kwargs)
        elif element_name == 'progressions':
            if element_value:
                self.draw_progressions(element_value, **kwargs)
        else:
            element = getattr(self, element_name)
            element.draw(self.canvas, element_value, **kwargs)

    def draw_page(self, names, **kwargs):
        if not getattr(self, 'canvas', None):
            self.create()

        kwargs['names'] = names
        element_values = {e: kwargs.pop(e, None) for e in self.elements}
        element_props = {e: {} for e in self.elements}
        for k in kwargs:
            if k == 'format_string' and 'progressions' in self.elements:
                element_props['progressions']['format_string'] = kwargs[k]
                continue
            for e in self.elements:
                if k.startswith(e+'_'):
                    p = k.replace(e+'_', '', 1)
                    element_props[e][p] = kwargs[k]
                    break

        for e in self.elements:
            self.draw_element(e, element_values[e], **element_props[e])

    def next_page(self):
        self.canvas.showPage()

    def save(self):
        self.canvas.save()
        self.overlay_packet.seek(0)

    def draw(self, names, **kwargs):
        if not getattr(self, 'canvas', None):
            self.create()
        if not isinstance(names[0], (tuple, list)):
            names = [names]
        var_kwargs = expand_kwargs(len(names), names=names, **kwargs)
        for vkwargs in var_kwargs:
            self.draw_page(**vkwargs)
            self.next_page()
        self.save()

    def merge_pages(self):
        template_packet = open_binary(templates, self.template_file)
        overlay = PdfFileReader(self.overlay_packet)
        for n in range(overlay.numPages):
            bracket = PdfFileReader(template_packet).getPage(0)
            bracket.mergePage(overlay.getPage(n))
            yield bracket


class TemplateLookup:
    key_field = 'template_file'
    sort_field = 'lookup_order'
    reserve_field = 'reserve_options'
    fields = [
        'format',
        'n_entrants',
        'n_in_winnners',
        'n_in_losers',
        'n_advance',
        'template_file',
        'bracket_size',
        'n_slots',
        'lookup_order',
        'legacy_code',
        'paper_size',
        'paper_orientation',
        'source',
        'elements'
    ]
    config = json.load(open_text(templates, 'config.json'))

    @classmethod
    def lookup(cls, key):
        for lkp in cls.config:
            if key == lkp[cls.key_field]:
                return lkp
        raise ValueError('No matching template found')

    @classmethod
    def get(cls, key):
        return Template(**cls.lookup(key))

    @classmethod
    def _search(cls, check_reserve=False, **params):
        best_key, best_sort = None, 1e8
        for conf in cls.config:
            lkp = conf
            if check_reserve:
                lkp = {**conf, **conf.get(cls.reserve_field, {})}
            if lkp[cls.sort_field] < best_sort:
                is_match = True
                for k in params:
                    if isinstance(lkp.get(k), list):
                        is_match &= (params[k] in lkp[k])
                    elif lkp.get(k, -999) is not None:
                        is_match &= (params[k] == lkp.get(k, -999))
                    if not is_match:
                        break
                if is_match:
                    best_key = lkp[cls.key_field]
                    best_sort = lkp[cls.sort_field]
        if best_key is None:
            raise ValueError('No matching template found')
        return best_key

    @classmethod
    def search(cls, format, n_advance=0, n_entrants=None,
               n_in_winners=None, n_in_losers=None, **params):
        valid_params = dict(format=format, n_advance=n_advance)
        if n_entrants:
            if n_in_winners or n_in_losers:
                warnings.warn('Field n_entrants supercedes fields'
                              'n_in_winners & n_in_losers')
            valid_params.update(n_entrants=n_entrants)
        elif n_in_winners and n_in_losers:
            valid_params.update(n_in_winners=n_in_winners,
                                n_in_losers=n_in_losers)
        else:
            raise KeyError('Missing required lookup field(s), '
                           'Must specify either n_entrants '
                           'or both n_in_winners and n_in_losers')
        for k in params:
            if k in cls.fields:
                valid_params[k] = params[k]
        try:
            match = cls._search(**valid_params)
        except ValueError:
            match = cls._search(check_reserve=True, **valid_params)
        return match
