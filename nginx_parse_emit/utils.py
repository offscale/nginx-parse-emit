from copy import copy
from operator import itemgetter
from string import Template

from offutils import pp


class DollarTemplate(Template):
    delimiter = '$'
    idpattern = r'[a-z][_a-z0-9]*'


def ensure_semicolon(s):  # type: (str) -> str or None
    if s is None:
        return s
    s = s.rstrip()
    return s if not len(s) or s[-1] == ';' else '{};'.format(s)


def merge_into(parent_block, *child_blocks):
    parent_block = copy(parent_block)
    parent_block[0][-1] += map(itemgetter(0), child_blocks)
    return parent_block
