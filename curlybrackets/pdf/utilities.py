
import re
from string import Formatter
from collections import defaultdict, OrderedDict
from datetime import datetime


NBSP = '\u00a0'
ENDA = '\u2013'


def cycle_list(length, lst):
    q, r = divmod(length, len(lst))
    return (lst * q + lst[:r])


def expand_kwargs(length, **kwargs):
    variable_kwargs = [{} for _ in range(length)]
    for k in kwargs:
        if (not isinstance(kwargs[k], (tuple, list))
                or len(kwargs[k]) != length):
            for i in range(length):
                variable_kwargs[i][k] = kwargs[k]
        else:
            for i in range(length):
                variable_kwargs[i][k] = kwargs[k][i]
    return variable_kwargs


def collapse_kwargs(variable_kwargs):
    kwargs = defaultdict(list)
    for var_kwargs in variable_kwargs:
        for k in var_kwargs:
            kwargs[k].append(var_kwargs[k])
    for k in kwargs:
        if len(kwargs[k]) != len(variable_kwargs):
            raise KeyError('Invalid variable_kwargs')
        elif all(v == kwargs[k][0] for v in kwargs[k]):
            kwargs[k] = kwargs[k][0]
    return kwargs


class ProgressionFormatter(Formatter):
    def vformat(self, format_string, args, kwargs):
        format_string = re.sub('&nbsp;', NBSP, format_string)
        return super().vformat(format_string, args, kwargs)

    def format_field(self, value, format_spec):
        if isinstance(value, (list, tuple)):
            formatted = [self.format_field(v, format_spec) for v in value]
            return '/'.join(OrderedDict.fromkeys(formatted))
        elif isinstance(value, datetime):
            formatted = super().format_field(value, format_spec)
            formatted = re.sub(':00(?!:)', '', formatted)
            if '%p' in format_spec or '%r' in format_spec:
                formatted = re.sub(':00(?!:)', '', formatted)
                formatted = re.sub('[AP]M',
                                   lambda m: m.group().lower(),
                                   formatted)
            formatted = formatted.replace(' ', NBSP)
            return formatted
        elif isinstance(value, int) and format_spec.endswith('O'):
            if value <= 0:
                raise ValueError('Integer must be positive for ordinal format')
            n = value
            if n > 1000:
                n = (n - 1) % 1000 + 1
            if n > 20:
                n = (n - 1) % 10 + 1
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n, 'th')
            return super().format_field(value, format_spec[:-1]) + suffix
        elif isinstance(value, str) and format_spec.endswith('w'):
            # Create non-breaking space format code 'w'
            formatted = super().format_field(value, format_spec[:-1])
            formatted = formatted.replace(' ', NBSP)
            return formatted
        return super().format_field(value, format_spec)
