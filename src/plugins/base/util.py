from typing import Iterable

from awaits.awaitable import awaitable


def escape_md(txt: str, ignores: Iterable = None):
    # fmt:off
    chars = [
        "[", "]", "(", ")", "{", "}", "_", "*", "~", "`", ">", "#", "+", "-", "=", "|",
        ".", "!"
    ]
    # fmt:on
    for c in chars:
        if ignores and (c in ignores):
            continue
        txt = txt.replace(c, f"\\{c}")
    return txt


async def async_wrapper(origin_func, *args, **kwargs):
    """异步调用包装"""

    @awaitable
    def wrapper_():
        return origin_func(*args, **kwargs)

    return await wrapper_()
