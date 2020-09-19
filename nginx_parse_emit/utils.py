from operator import itemgetter
from platform import python_version_tuple

from sys import version

if version[0] == "2":
    from cStringIO import StringIO

else:
    from functools import reduce
    from io import StringIO

from copy import copy
from itertools import filterfalse
from os import remove, path
from string import Template
from tempfile import mkstemp

from fabric.contrib.files import exists
from fabric.operations import get, put
from nginxparser import loads, dumps, load


class DollarTemplate(Template):
    delimiter = "$"
    idpattern = r"[a-z][_a-z0-9]*"


def ensure_semicolon(s):  # type: (str) -> str or None
    if s is None:
        return s
    s = s.rstrip()
    return s if not len(s) or s[-1] == ";" else "{};".format(s)


def _copy_or_marshal(block):  # type: (str or list) -> list
    return copy(block) if isinstance(block, list) else loads(block)


def merge_into(
    server_name, parent_block, *child_blocks
):  # type: (str, str or list, *list) -> list
    parent_block = _copy_or_marshal(parent_block)

    server_name_idx = -1
    indicies = set()
    break_ = False

    for i, tier in enumerate(parent_block):
        for j, statement in enumerate(tier):
            for k, stm in enumerate(statement):
                if statement[k][0] == "server_name" and statement[k][1] == server_name:
                    server_name_idx = i
                    indicies.add(k)
                    if break_:
                        break
                elif statement[k][0] == "listen" and statement[k][1].startswith("443"):
                    break_ = True
                    if k in indicies:
                        break

    server_name_idx += 1

    if not len(indicies):
        return parent_block

    length = len(parent_block[-1])
    if server_name_idx >= length:
        server_name_idx = length - 1

    parent_block[-1][server_name_idx] += list(
        map(
            lambda child_block: child_block[0]
            if isinstance(child_block[0], list)
            else loads(child_block)[0],
            child_blocks,
        )
    )
    parent_block[-1][server_name_idx] = list(
        reversed(uniq(reversed(parent_block[-1][-1]), itemgetter(0)))
    )

    return parent_block


def merge_into_str(
    server_name, parent_block, *child_blocks
):  # type: (str or list, *list) -> str
    return dumps(merge_into(server_name, parent_block, *child_blocks))


def upsert_by_location(
    server_name, location, parent_block, child_block
):  # type: (str, str or list, str or list) -> list
    return merge_into(
        server_name,
        remove_by_location(_copy_or_marshal(parent_block), location),
        child_block,
    )


def remove_by_location(parent_block, location):  # type: (list, str) -> list
    parent_block = _copy_or_marshal(parent_block)
    parent_block = list(
        map(
            lambda block: list(
                map(
                    lambda subblock: list(
                        filterfalse(
                            lambda subsubblock: len(subsubblock)
                            and len(subsubblock[0]) > 1
                            and subsubblock[0][1] == location,
                            subblock,
                        )
                    ),
                    block,
                )
            ),
            parent_block,
        )
    )
    return parent_block


def _prevent_slash(s):  # type: (str) -> str
    return s[1:] if s.startswith("/") else s


def apply_attributes(
    block, attribute, append=False
):  # type: (str or list, str or list, bool) -> list
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
        if (
            prev_key is not None
            and prev_key == subblock[0]
            and prev_key in ("server_name", "listen")
        ):
            continue
        subseq_removed.append(subblock)
        prev_key = subblock[0]
    subseq_removed.reverse()
    block[0][1] = subseq_removed

    return block


def upsert_upload(new_conf, name="default", use_sudo=True):
    conf_name = "/etc/nginx/sites-enabled/{nginx_conf}".format(nginx_conf=name)
    if not conf_name.endswith(".conf") and not exists(conf_name):
        conf_name += ".conf"
    # cStringIO.StringIO, StringIO.StringIO, TemporaryFile, SpooledTemporaryFile all failed :(
    tempfile = mkstemp(name)[1]
    get(remote_path=conf_name, local_path=tempfile, use_sudo=use_sudo)
    with open(tempfile, "rt") as f:
        conf = load(f)
    new_conf = new_conf(conf)
    remove(tempfile)

    sio = StringIO()
    sio.write(dumps(new_conf))
    return put(sio, conf_name, use_sudo=use_sudo)


def get_parsed_remote_conf(
    conf_name, suffix="nginx", use_sudo=True
):  # type: (str, str, bool) -> [str]
    if not conf_name.endswith(".conf") and not exists(conf_name):
        conf_name += ".conf"
    # cStringIO.StringIO, StringIO.StringIO, TemporaryFile, SpooledTemporaryFile all failed :(
    tempfile = mkstemp(suffix)[1]
    get(remote_path=conf_name, local_path=tempfile, use_sudo=use_sudo)
    with open(tempfile, "rt") as f:
        conf = load(f)
    remove(tempfile)
    return conf


def ensure_nginxparser_instance(conf_file):  # type: (str) -> [[[str]]]
    if isinstance(conf_file, list):
        return conf_file
    elif hasattr(conf_file, "read"):
        return load(conf_file)
    elif path.isfile(conf_file):
        with open(conf_file, "rt") as f:
            return load(f)
    else:
        return loads(conf_file)


def uniq(iterable, key=lambda x: x):
    """
    Remove duplicates from an iterable. Preserves order.
    :type iterable: Iterable[Ord => A]
    :param iterable: an iterable of objects of any orderable type
    :type key: Callable[A] -> (Ord => B)
    :param key: optional argument; by default an item (A) is discarded
    if another item (B), such that A == B, has already been encountered and taken.
    If you provide a key, this condition changes to key(A) == key(B); the callable
    must return orderable objects.
    """

    # Enumerate the list to restore order lately; reduce the sorted list; restore order
    def append_unique(acc, item):
        return acc if key(acc[-1][1]) == key(item[1]) else acc.append(item) or acc

    srt_enum = sorted(enumerate(iterable), key=lambda item: key(item[1]))
    return [item[1] for item in sorted(reduce(append_unique, srt_enum, [srt_enum[0]]))]
