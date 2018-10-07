from __future__ import print_function

from cStringIO import StringIO
from copy import copy
from itertools import imap, ifilterfalse
from os import remove
from string import Template
from tempfile import mkstemp

from fabric.contrib.files import exists
from fabric.operations import get, put
from nginxparser import loads, dumps, load


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


def merge_into_str(parent_block, *child_blocks):  # type: (str or list, *list) -> str
    return dumps(merge_into(parent_block, *child_blocks))


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


def apply_attributes(block, attribute, append=False):  # type: (str or list, str or list, bool) -> list
    block = _copy_or_marshal(block)
    attribute = _copy_or_marshal(attribute)

    if append:
        block[-1][-1] += attribute
    else:
        changed = False
        for bid, _block in enumerate(block[-1]):
            for sid, subblock in enumerate(_block):
                if isinstance(subblock[0], list):
                    block[-1][bid] = attribute + [block[-1][bid][sid]]
                    changed = True
                    break

        if not changed:
            block[-1][-1] += attribute

    # TODO: Generalise these lines to a `remove_duplicates` or `remove_consecutive_duplicates` function

    prev_key = None
    subseq_removed = []
    if not isinstance(block[0][1], list):
        return block

    block[0][1].reverse()
    for subblock in block[0][1]:
        if prev_key is not None and prev_key == subblock[0] and prev_key in ('server_name', 'listen'):
            continue
        subseq_removed.append(subblock)
        prev_key = subblock[0]
    subseq_removed.reverse()
    block[0][1] = subseq_removed

    return block


def upsert_upload(new_conf, name='default', use_sudo=True):
    conf_name = '/etc/nginx/sites-enabled/{nginx_conf}'.format(nginx_conf=name)
    if not conf_name.endswith('.conf') and not exists(conf_name):
        conf_name += '.conf'
    # cStringIO.StringIO, StringIO.StringIO, TemporaryFile, SpooledTemporaryFile all failed :(
    tempfile = mkstemp(name)[1]
    get(remote_path=conf_name, local_path=tempfile, use_sudo=use_sudo)
    with open(tempfile, 'rt') as f:
        conf = load(f)
    new_conf = new_conf(conf)
    remove(tempfile)

    sio = StringIO()
    sio.write(dumps(new_conf))
    return put(sio, conf_name, use_sudo=use_sudo)
