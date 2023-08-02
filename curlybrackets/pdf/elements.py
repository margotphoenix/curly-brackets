import math
import warnings

from reportlab.lib.colors import Color
from reportlab.platypus import Paragraph, Frame, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.textobject import PDFTextObject as _PDFTextObject

from curlybrackets.pdf.utilities import expand_kwargs, cycle_list


def gray2color(g):
    if g is not None:
        return Color(g, g, g)


class PDFTextObject(_PDFTextObject):
    def __init__(self, canvas, x=0, y=0, direction=None):
        super().__init__(canvas, x, y, direction)
        self._transform = [1, 0, 0, 1]

    def setFont(self, fontname, fontsize):
        if fontname != self._fontname or fontsize != self._fontsize:
            super().setFont(fontname, fontsize)

    def setHorizScale(self, hscale):
        if not hasattr(self, '_hscale') or hscale != self._hscale:
            super().setHorizScale(hscale)
            self._hscale = hscale

    def setFillGray(self, gray):
        if not hasattr(self, '_gray') or gray != self._gray:
            super().setFillGray(gray)
            self._gray = gray

    def setTextTransform(self, a, b, c, d, e, f):
        super().setTextTransform(a, b, c, d, e, f)
        self._transform = [a, b, c, d]


class Element:
    required_args = []
    optional_args = {}

    def __init__(self, **kwargs):
        missing = [key for key in self.required_args if key not in kwargs]
        if missing:
            raise AttributeError(
                'Missing required argument(s): ' + ', '.join(missing)
            )
        all_args = {**self.optional_args, **kwargs}
        for key in all_args:
            setattr(self, key, all_args[key])

    @classmethod
    def frame_args(cls):
        return (cls.required_args + list(cls.optional_args))

    @classmethod
    def filter_kwargs(cls, dct=None, **kwargs):
        if dct is None:
            dct = {}
        dct = {**dct, **kwargs}
        frame_args = cls.frame_args()
        frame_kwargs, other_kwargs = {}, {}
        for key in dct:
            if key in frame_args:
                frame_kwargs[key] = dct[key]
            else:
                other_kwargs[key] = dct[key]
        return frame_kwargs, other_kwargs

    @classmethod
    def without_meta(cls, **kwargs):
        frame_kwargs = cls.filter_kwargs(kwargs)[0]
        return cls(**frame_kwargs)

    def as_dict(self):
        dct = {}
        for key in self.frame_args():
            item = getattr(self, key)
            if hasattr(item, 'copy'):
                dct[key] = item.copy()
            else:
                dct[key] = item
        return dct

    def clone(self, **kwargs):
        dct = {**self.as_dict(), **kwargs}
        return self.__class__(**dct)

    def _draw(self):
        pass

    def draw(self):
        self._draw()


class _TextFieldElement(Element):
    required_args = ['width']
    optional_args = {'fontsize': None,
                     'fontname': None,
                     'min_hscale': 100,
                     'alignment': 'left',
                     'textgray': 0}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if isinstance(self.alignment, int):
            self.alignment = ['left', 'center', 'right'][self.alignment]
        self.alignment = self.alignment.lower()

    def _draw(self, txobj, line):
        if not isinstance(line, str):
            line = str(line)
        fontsize = self.fontsize if self.fontsize else txobj._fontsize
        fontname = self.fontname if self.fontname else txobj._fontname
        canv = txobj._canvas

        line = line.strip()
        if line.startswith('~~') and line.endswith('~~') and len(line) >= 5:
            line = line[2:-3]
            strike = True
        else:
            strike = False

        line_width = canv.stringWidth(line, fontname, fontsize)
        hscale = 100 * self.width / (line_width if line_width > 0 else 1e-5)
        while hscale < self.min_hscale:
            fontsize -= 0.25
            line_width = canv.stringWidth(line, fontname, fontsize)
            hscale = 100 * self.width / line_width
        if hscale > 100:
            hscale = 100
        else:
            line_width = self.width

        if self.alignment == 'right':
            shift = self.width - line_width
        elif self.alignment in ['center', 'centre']:
            shift = 0.5 * (self.width - line_width)
        else:
            shift = 0
        txobj.setXPos(shift)
        txobj.setFont(fontname, fontsize)
        txobj.setHorizScale(hscale)
        txobj.setFillGray(self.textgray)
        txobj._textOut(line)
        txobj.setXPos(-shift)

        if strike:
            a, b, c, d = txobj._transform
            determ = a * d - b * c
            dx1 = shift
            dx2 = shift + line_width
            dy = 0.25 * fontsize
            x1 = txobj.getX() + (dx1 * d - dy * b) / determ
            x2 = txobj.getX() + (dx2 * d - dy * b) / determ
            y1 = txobj.getY() + (dy * a - dx1 * c) / determ
            y2 = txobj.getY() + (dy * a - dx2 * c) / determ
            osc = canv._strokeColorObj
            if osc != (self.textgray, self.textgray, self.textgray):
                canv.setStrokeGray(self.textgray)
            canv.line(x1, y1, x2, y2)

    def draw(self, txobj, line=None, **kwargs):
        if line:
            frame_kwargs = self.filter_kwargs(kwargs)[0]
            if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
                self.clone(**frame_kwargs)._draw(txobj, line)
            else:
                self._draw(txobj, line)


class TextFieldElement(Element):
    required_args = ['x', 'y', 'width']
    optional_args = {'rotation': 0,
                     'fontsize': None,
                     'fontname': None,
                     'min_hscale': 100,
                     'alignment': 'left',
                     'textgray': 0}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cos = math.cos(self.rotation * math.pi / 180)
        self.sin = math.sin(self.rotation * math.pi / 180)

    def _draw(self, canvas, line, **kwargs):
        txobj = PDFTextObject(canvas)
        txobj.setTextTransform(self.cos, self.sin, -self.sin, self.cos,
                               self.x, self.y)

        lineframe = _TextFieldElement.without_meta(**self.as_dict(), **kwargs)
        lineframe._draw(txobj, line)

        txobj.setHorizScale(100)
        canvas.drawText(txobj)

    def draw(self, canvas, text=None, **kwargs):
        if text:
            frame_kwargs, other_kwargs = self.filter_kwargs(kwargs)
            if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
                self.clone(**frame_kwargs)._draw(canvas, text, **other_kwargs)
            else:
                self._draw(canvas, text, **other_kwargs)


class TextListElement(TextFieldElement):
    required_args = ['x0', 'y0', 'width', 'max_lines']
    optional_args = {'rotation': 0,
                     'dx': [0],
                     'dy': [0],
                     'fontsize': None,
                     'fontname': None,
                     'min_hscale': 100,
                     'alignment': 'left',
                     'textgray': 0}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dx = cycle_list(self.max_lines, self.dx)
        self.dy = cycle_list(self.max_lines, self.dy)

    def _draw(self, canvas, lines, **kwargs):
        if not isinstance(lines, (list, tuple)):
            lines = [lines]

        if len(lines) > self.max_lines:
            warnings.warn('Frame cannot hold all lines')

        txobj = PDFTextObject(canvas)
        txobj.setTextTransform(self.cos, self.sin, -self.sin, self.cos,
                               self.x0, self.y0)

        n_lines = min(len(lines), self.max_lines)
        var_kwargs = expand_kwargs(len(lines), **self.as_dict(), **kwargs)
        for i in range(n_lines):
            if lines[i] is not None:
                lineframe = _TextFieldElement.without_meta(**var_kwargs[i])
                lineframe._draw(txobj, lines[i])
            if i + 1 < n_lines:
                txobj.moveCursor((self.dx[i] * self.cos - self.dy[i] * self.sin),
                                 (self.dx[i] * self.sin + self.dy[i] * self.cos))

        txobj.setHorizScale(100)
        canvas.drawText(txobj)

    def draw(self, canvas, lines=None, **kwargs):
        if lines:
            frame_kwargs, other_kwargs = self.filter_kwargs(kwargs)
            if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
                self.clone(**frame_kwargs)._draw(canvas, lines, **other_kwargs)
            else:
                self._draw(canvas, lines, **other_kwargs)


class RectElement(Element):
    required_args = ['x', 'y', 'width', 'height']
    optional_args = {'backgray': 1,
                     'bordergray': None,
                     'borderwidth': 0}

    def fill(self, canvas):
        canvas.saveState()
        if self.backgray:
            canvas.setFillGray(self.backgray)
            canvas.rect(self.x, self.y, self.width, self.height,
                        stroke=0, fill=1)
        if self.bordergray and self.borderwidth:
            canvas.setStrokeColor(self.bordergray)
            canvas.setLineWidth(self.borderwidth)
            canvas.rect(self.x, self.y, self.width, self.height,
                        stroke=1, fill=0)
        canvas.restoreState()

    _draw = fill

    def draw(self, canvas, **kwargs):
        frame_kwargs = self.filter_kwargs(kwargs)[0]
        if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
            self.clone(**frame_kwargs)._draw(canvas)
        else:
            self._draw(canvas)


class _SlotElement(Element):
    required_args = ['width', 'height']
    optional_args = {'fontsize': None,
                     'fontname': None,
                     'min_hscale': 100,
                     'alignment': 'left',
                     'valign': 'middle',
                     'textgray': 0, 
                     'margin': 0}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if isinstance(self.alignment, int):
            self.alignment = ['left', 'center', 'right'][self.alignment]
        self.alignment = self.alignment.lower()

        if isinstance(self.valign, int):
            self.valign = ['bottom', 'middle', 'top'][self.valign]
        self.valign = self.valign.lower()

        if isinstance(self.margin, (int, float)):
            self.margin = {k: self.margin
                           for k in ['top', 'right', 'bottom', 'left']}
        elif isinstance(self.margin, (list, tuple)):
            while len(self.margin) < 4:
                self.margin = list(self.margin) * 2
            self.margin = {k: m for k, m in zip(['top', 'right', 'bottom', 'left'],
                                                self.margin)}
        else:
            self.margin = {k: self.margin.get(k, 0)
                           for k in ['top', 'right', 'bottom', 'left']}

    def _draw(self, txobj, line):
        if not isinstance(line, str):
            line = str(line)
        fontsize = self.fontsize if self.fontsize else txobj._fontsize
        fontname = self.fontname if self.fontname else txobj._fontname
        canv = txobj._canvas

        line = line.strip()
        if line.startswith('~~') and line.endswith('~~') and len(line) >= 5:
            line = line[2:-3]
            strike = True
        else:
            strike = False

        avail_width = self.width - self.margin['left'] - self.margin['right']
        avail_height = self.height - self.margin['top'] - self.margin['bottom']

        line_width = canv.stringWidth(line, fontname, fontsize)
        hscale = 100 * avail_width / (line_width if line_width > 0 else 1e-5)
        while hscale < self.min_hscale:
            fontsize -= 0.25
            line_width = canv.stringWidth(line, fontname, fontsize)
            hscale = 100 * avail_width / line_width
        if hscale > 100:
            hscale = 100
        else:
            line_width = avail_width

        if self.alignment == 'right':
            hshift = self.width - self.margin['right'] - line_width
        elif self.alignment in ['center', 'centre']:
            hshift = self.margin['left'] + 0.5 * (avail_width - line_width)
        else:
            hshift = self.margin['left']
        if self.valign == 'top':
            vshift = self.height - self.margin['top'] - fontsize
        elif self.valign == 'middle':
            vshift = self.margin['bottom'] + 0.5 * (avail_height - fontsize)
        else:
            vshift = self.margin['bottom']
        # vshift = 3
        txobj.moveCursor(hshift, -vshift)
        txobj.setFont(fontname, fontsize)
        txobj.setHorizScale(hscale)
        txobj.setFillGray(self.textgray)
        txobj._textOut(line)
        txobj.moveCursor(-hshift, vshift)

        if strike:
            a, b, c, d = txobj._transform
            determ = a * d - b * c
            dx1 = hshift
            dx2 = hshift + line_width
            dy = vshift + 0.25 * fontsize
            x1 = txobj.getX() + (dx1 * d - dy * b) / determ
            x2 = txobj.getX() + (dx2 * d - dy * b) / determ
            y1 = txobj.getY() + (dy * a - dx1 * c) / determ
            y2 = txobj.getY() + (dy * a - dx2 * c) / determ
            osc = canv._strokeColorObj
            if osc != (self.textgray, self.textgray, self.textgray):
                canv.setStrokeGray(self.textgray)
            canv.line(x1, y1, x2, y2)

    def draw(self, txobj, line=None, **kwargs):
        if line:
            frame_kwargs = self.filter_kwargs(kwargs)[0]
            if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
                self.clone(**frame_kwargs)._draw(txobj, line)
            else:
                self._draw(txobj, line)


class SlotElement(TextFieldElement):
    required_args = ['x', 'y', 'width', 'height']
    optional_args = {'rotation': 0,
                     'fontsize': None,
                     'fontname': None,
                     'min_hscale': 100,
                     'alignment': 'left',
                     'textgray': 0,
                     'margin': 0, 
                     'backgray': 0,
                     'bordergray': None,
                     'borderwidth': 0}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if isinstance(self.margin, (int, float)):
            self.margin = {k: self.margin
                           for k in ['top', 'right', 'bottom', 'left']}
        elif isinstance(self.margin, (list, tuple)):
            while len(self.margin) < 4:
                self.margin = list(self.margin) * 2
            self.margin = {k: m for k, m in zip(['top', 'right', 'bottom', 'left'],
                                                self.margin)}
        else:
            self.margin = {k: self.margin.get(k, 0)
                           for k in ['top', 'right', 'bottom', 'left']}
        self.rect = RectElement.without_meta(**self.as_dict())

    def _draw(self, canvas, content, **kwargs):
        if content is None:
            self.rect._draw(canvas)
        else:
            txobj = PDFTextObject(canvas)
            txobj.setTextTransform(
                self.cos, self.sin, -self.sin, self.cos,
                self.x, self.y)

            lineframe = _SlotElement.without_meta(**self.as_dict(), **kwargs)
            lineframe._draw(txobj, content)

            txobj.setHorizScale(100)
            canvas.drawText(txobj)

    def draw(self, canvas, content=None, **kwargs):
        frame_kwargs, other_kwargs = self.filter_kwargs(kwargs)
        if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
            self.clone(**frame_kwargs)._draw(canvas, content, **other_kwargs)
        else:
            self._draw(canvas, content, **other_kwargs)


class SlotListElement(SlotElement):
    required_args = ['x', 'y', 'width', 'height', 'num_slots']
    optional_args = {'rotation': 0,
                     'fontsize': None,
                     'fontname': None,
                     'min_hscale': 100,
                     'alignment': 'left',
                     'textgray': 0,
                     'margin': 0,
                     'backgray': 0.01,
                     'bordergray': None,
                     'borderwidth': 0}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not isinstance(self.x, (list, tuple)):
            self.x = [self.x] * self.num_slots
        if not isinstance(self.y, (list, tuple)):
            self.y = [self.y] * self.num_slots

        var_kwargs = expand_kwargs(self.num_slots, **self.as_dict())
        self.rects = [RectElement.without_meta(**vk) for vk in var_kwargs]

    def _draw(self, canvas, contents, **kwargs):
        if not isinstance(contents, (list, tuple)):
            contents = [contents]

        if len(contents) > self.num_slots:
            warnings.warn('Lines exceed available slots')

        txobj = PDFTextObject(canvas)
        txobj.setTextTransform(self.cos, self.sin, -self.sin, self.cos,
                               self.x[0], self.y[0])
        rects_to_draw = []

        var_kwargs = expand_kwargs(len(contents), **self.as_dict(), **kwargs)
        for i in range(self.num_slots):
            if i >= len(contents) or contents[i] is None:
                rects_to_draw.append(i)
            elif contents[i] != '':
                lineframe = _SlotElement.without_meta(**var_kwargs[i])
                lineframe._draw(txobj, contents[i])
            if i + 1 < self.num_slots:
                dx = self.x[i] - self.x[i+1]
                dy = self.y[i] - self.y[i+1]
                txobj.moveCursor((dx * self.cos - dy * self.sin),
                                 (dx * self.sin + dy * self.cos))

        txobj.setHorizScale(100)
        canvas.drawText(txobj)

        for i in rects_to_draw:
            self.rects[i]._draw(canvas)


    def draw(self, canvas, contents=None, **kwargs):
        frame_kwargs, other_kwargs = self.filter_kwargs(kwargs)
        if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
            self.clone(**frame_kwargs)._draw(canvas, contents, **other_kwargs)
        else:
            self._draw(canvas, contents, **other_kwargs)


class ParagraphElement(RectElement):
    required_args = ['x', 'y', 'width', 'height']
    optional_args = {'alignment': 0,
                     'fontsize': None,
                     'fontname': None,
                     'textgray': 0,
                     'backgray': None,
                     'bordergray': None,
                     'borderwidth': 0,
                     'valign': 2}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if isinstance(self.alignment, str):
            alignment = self.alignment.lower()
            self.alignment = {'left': 0, 'center': 1, 'right': 2}[alignment]
        if isinstance(self.valign, str):
            valign = self.valign.lower()
            self.valign = {'bottom': 0, 'middle': 1, 'top': 2}[valign]

    def _build_frame(self, canvas):
        self.fill(canvas)
        frame = Frame(self.x, self.y, self.width, self.height,
                      leftPadding=0, bottomPadding=0,
                      rightPadding=0, topPadding=0)
        return frame

    def _build_style(self, canvas):
        fontsize = self.fontsize if self.fontsize else canvas._fontsize
        fontname = self.fontname if self.fontname else canvas._fontname
        style = ParagraphStyle('Par', fontSize=fontsize, fontName=fontname,
                               leading=fontsize * 1.2,
                               alignment=self.alignment, valign=self.valign,
                               textColor=gray2color(self.textgray),
                               backColor=None, borderColor=None, borderWidth=0)
        return style

    @staticmethod
    def _generate_tablestyle(style):
        halign = ['LEFT', 'CENTER', 'RIGHT'][style.alignment]
        valign = ['BOTTOM', 'MIDDLE', 'TOP'][style.valign]

        cmds = [
            ('ALIGNMENT', (0, 0), (-1, -1), halign),
            ('VALIGN', (0, 0), (-1, -1), valign),
            ('FONTSIZE', (0, 0), (-1, -1), style.fontSize),
            ('FONTNAME', (0, 0), (-1, -1), style.fontName),
            ('LEADING', (0, 0), (-1, -1), style.leading),
            ('TEXTCOLOR', (0, 0), (-1, -1), style.textColor),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
        ]
        if style.backColor:
            cmds.append(('BACKGROUND', (0, 0), (-1, -1), style.backColor))
        if style.borderColor and style.borderWidth:
            cmds.append(
                ('GRID', (0, 0), (-1, -1), style.borderWidth, style.borderColor)
            )
        return TableStyle(cmds)

    def _draw(self, canvas, text):
        frame = self._build_frame(canvas)
        style = self._build_style(canvas)
        par = Paragraph(text, style)
        check = len(frame.split(par, canvas))
        while check != 1:
            style.fontSize -= 0.25
            style.leading -= 0.3
            par = Paragraph(text, style)
            check = len(frame.split(par, canvas))
        tstyle = self._generate_tablestyle(style)
        table = Table([[par]], rowHeights=[self.height],
                      colWidths=[self.width], style=tstyle,
                      vAlign=['BOTTOM', 'MIDDLE', 'TOP'][self.valign],
                      hAlign=['LEFT', 'CENTER', 'RIGHT'][self.alignment])
        frame.addFromList([table], canvas)

    def draw(self, canvas, text='', **kwargs):
        if text is not None:
            frame_kwargs = self.filter_kwargs(kwargs)[0]
            if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
                self.clone(**frame_kwargs)._draw(canvas, text)
            else:
                self._draw(canvas, text)


class ItemListElement(ParagraphElement):
    required_args = ['x', 'y', 'width', 'height']
    optional_args = {'alignment': 0,
                     'fontsize': None,
                     'fontname': None,
                     'textgray': 0,
                     'backgray': None,
                     'bordergray': None,
                     'borderwidth': 0,
                     'bullet': None,
                     'valign': 2,
                     'section_header': None,
                     'col_space': 1.8}

    def _draw(self, canvas, items):
        frame = self._build_frame(canvas)
        style = self._build_style(canvas)
        avail_height = self.height

        if self.section_header:
            par = Paragraph(self.section_header, style)
            frame.addFromList([par], canvas)
            avail_height -= style.leading

        if self.bullet:
            items_txt = [f'{self.bullet} {n}' for n in items]
        else:
            items_txt = items

        istyle = style.clone('Item')
        nrows = math.floor(avail_height / istyle.leading)
        ncols = math.ceil(len(items_txt) / nrows)
        items_ext = items_txt + [''] * (nrows * ncols - len(items_txt))

        items_grid = [items_ext[i*nrows:(i+1)*nrows] for i in range(ncols)]
        items_table = [['\n'.join(col) for col in items_grid]]

        col_widths = [max(canvas.stringWidth(t, istyle.fontName, istyle.fontSize)
                          for t in col) + istyle.fontSize * self.col_space
                      for col in items_grid]
        row_heights = [istyle.leading * nrows]
        tstyle = self._generate_tablestyle(istyle)

        table = Table(items_table, rowHeights=row_heights,
                      colWidths=col_widths, style=tstyle,
                      vAlign=['BOTTOM', 'MIDDLE', 'TOP'][self.valign],
                      hAlign=['LEFT', 'CENTER', 'RIGHT'][self.alignment])
        check = 0 if sum(col_widths) > self.width else frame.add(table, canvas)
        while check == 0:
            istyle.fontSize -= 0.25
            istyle.leading -= 0.3

            nrows = math.floor(avail_height / istyle.leading)
            ncols = math.ceil(len(items_txt) / nrows)
            items_ext = items_txt + [''] * (nrows * ncols - len(items_txt))

            items_grid = [items_ext[i*nrows:(i+1)*nrows] for i in range(ncols)]
            items_table = [['\n'.join(col) for col in items_grid]]

            col_widths = [max(canvas.stringWidth(t, istyle.fontName, istyle.fontSize)
                              for t in col) + istyle.fontSize * self.col_space
                          for col in items_grid]
            row_heights = [istyle.leading * nrows]
            tstyle = self._generate_tablestyle(istyle)

            table = Table(items_table, rowHeights=row_heights,
                          colWidths=col_widths, style=tstyle,
                          vAlign=['BOTTOM', 'MIDDLE', 'TOP'][self.valign],
                          hAlign=['LEFT', 'CENTER', 'RIGHT'][self.alignment])
            check = 0 if sum(col_widths) > self.width else frame.add(table, canvas)

    def draw(self, canvas, items=None, **kwargs):
        if items:
            frame_kwargs = self.filter_kwargs(kwargs)[0]
            if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
                self.clone(**frame_kwargs)._draw(canvas, items)
            else:
                self._draw(canvas, items)
        elif self.section_header:
            frame = self._build_frame(canvas)
            style = self._build_style(canvas)
            par = Paragraph(self.section_header, style)
            frame.addFromList([par], canvas)


class ImageElement(RectElement):
    required_args = ['x', 'y', 'width', 'height']
    optional_args = {'backgray': 1,
                     'bordergray': None,
                     'borderwidth': 0}

    def _draw(self, canvas, image=None):
        self.fill(canvas)
        if image:
            canvas.drawImage(image, self.x, self.y, self.width, self.height,
                             preserveAspectRatio=True)

    def draw(self, canvas, image=None, **kwargs):
        frame_kwargs = self.filter_kwargs(kwargs)[0]
        if any(getattr(self, k) != frame_kwargs[k] for k in frame_kwargs):
            self.clone(**frame_kwargs)._draw(canvas, image)
        else:
            self._draw(canvas, image)
