from typing import Iterable


def escape_md(txt: str, ignores: Iterable = None):
    chars = [
        '[', ']', '(', ')', '_', '*', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'
    ]
    for c in chars:
        if ignores and (c in ignores):
            continue
        txt = txt.replace(c, f'\\{c}')
    return txt
