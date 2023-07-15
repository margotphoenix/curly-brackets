

from reportlab.lib.units import inch, cm, pica


class Length:
    def __init__(self, size, unit):
        self.size = size
        if unit in ['inch', 'in']:
            self.unit = 'in'
            self._scale = inch
        elif unit in ['cm', 'mm']:
            self.unit = 'cm'
            self._scale = cm
            if unit == 'mm':
                self.size = self.size / 10
        elif unit in ['pica']:
            self.unit = 'pica'
            self._scale = pica
        else:
            self.unit = 'pt'
            self._scale = 1

    def __call__(self):
        return self.size * self._scale

    def __repr__(self):
        return '{} {}'.format(self.size, self.unit)


class Page:
    def __init__(self, width, height, unit='pt'):
        self.width = Length(width, unit)
        self.height = Length(height, unit)

    @property
    def size(self):
        return (self.width(), self.height())

    def flip(self):
        self.width, self.height = self.height, self.width


def get_paper(size_name, orientation='landscape'):
    if size_name in ['US Letter']:
        paper = Page(11, 8.5, 'in')
    elif size_name in ['US Legal']:
        paper = Page(14, 8.5, 'in')
    elif size_name in ['US Tabloid']:
        paper = Page(17, 11, 'in')
    if orientation == 'portrait':
        paper.flip()
    return paper
