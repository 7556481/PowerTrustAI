"""Explicit ASCII decimal / US thousands convention, never locale inference."""
from decimal import Decimal
import re

VERSION = 'ascii-decimal-us-grouping-v1'
NUMBER = r'-?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?'
TOKEN = re.compile(NUMBER)

def parse_number(raw):
    if type(raw) is not str or TOKEN.fullmatch(raw) is None:
        raise ValueError('number: ASCII decimal with optional three-digit comma groups required')
    normalized = raw.replace(',', '')
    value = Decimal(normalized)
    return {'raw': raw, 'normalized': normalized, 'value': float(value),
            'number_format': VERSION}

def quantities(text, units):
    # Consume the entire numeric-looking token. Invalid groups cannot expose a
    # valid trailing suffix to a later search match.
    pattern = re.compile(r'(?<![\w.,+\-])([-+0-9][0-9.,+\-]*)\s*(' +
                         '|'.join(re.escape(u) for u in sorted(units, key=len, reverse=True)) + r')\b')
    output = []
    for match in pattern.finditer(text):
        trace = parse_number(match.group(1))
        output.append({**trace, 'unit': match.group(2),
                       'start_offset': match.start(1), 'end_offset': match.end(1)})
    return tuple(output)
