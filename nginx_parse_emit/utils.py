from copy import copy
from itertools import imap, ifilterfalse
from operator import itemgetter
from string import Template


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
    parent_block[-1][-1] += map(itemgetter(0), child_blocks)
    return parent_block


def upsert_by_location(location, parent_block, child_block):
    parent_block = copy(parent_block)

    parent_block = map(lambda block:
                       list(imap(lambda subblock:
                                 list(ifilterfalse(
                                     lambda subsubblock: len(subsubblock) and len(subsubblock[0]) > 1 and
                                                         subsubblock[0][1] == location,
                                     subblock)),
                                 block)),
                       parent_block)

    return merge_into(parent_block, child_block)
