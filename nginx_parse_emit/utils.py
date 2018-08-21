from copy import copy
from itertools import imap, ifilterfalse
from string import Template

from nginxparser import loads


class DollarTemplate(Template):
    delimiter = '$'
    idpattern = r'[a-z][_a-z0-9]*'


def ensure_semicolon(s):  # type: (str) -> str or None
    if s is None:
        return s
    s = s.rstrip()
    return s if not len(s) or s[-1] == ';' else '{};'.format(s)


def _copy_or_marshal(block):  # type: (str or list) -> list
    return copy(block) if isinstance(block, list) else loads(block)


def merge_into(parent_block, *child_blocks):  # type: (str or list, *list) -> list
    parent_block = _copy_or_marshal(parent_block)
    parent_block[-1][-1] += map(
        lambda child_block: child_block[0] if isinstance(child_block[0], list) else loads(child_block)[0],
        child_blocks
    )
    return parent_block


def upsert_by_location(location, parent_block, child_block):  # type: (str, str or list, str or list) -> list
    return merge_into(remove_by_location(_copy_or_marshal(parent_block), location), child_block)


def remove_by_location(parent_block, location):  # type: (list, str) -> list
    parent_block = _copy_or_marshal(parent_block)
    parent_block = map(lambda block:
                       list(imap(lambda subblock:
                                 list(ifilterfalse(
                                     lambda subsubblock: len(subsubblock) and len(subsubblock[0]) > 1 and
                                                         subsubblock[0][1] == location,
                                     subblock)),
                                 block)),
                       parent_block)
    return parent_block


def _prevent_slash(s):  # type: (str) -> str
    return s[1:] if s.startswith('/') else s