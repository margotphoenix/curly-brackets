

from reportlab.lib.units import inch, cm, mm, pica


class Length:
    def __init__(self, value, unit=None):
        self.value = value
        if unit is None or unit in ['points', 'pt']:
            self.unit = 'pt'
            self._scale = 1
        elif unit in ['inch', 'in']:
            self.unit = 'in'
            self._scale = inch
        elif unit in ['cm']:
            self.unit = 'cm'
            self._scale = cm
        elif unit in ['mm']:
            self.unit = 'mm'
            self._scale = mm
        elif unit in ['pica']:
            self.unit = 'pica'
            self._scale = pica
        else:
            raise AttributeError(
                f'Unrecognized unit: {unit}'
            )

    def __call__(self):
        return self.value * self._scale

    def __repr__(self):
        return '{} {}'.format(self.value, self.unit)

    @property
    def size(self):
        return self()
