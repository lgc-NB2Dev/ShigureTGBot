import time
from typing import Callable, Iterable, Optional, TypeVar

from awaits.awaitable import awaitable
from typing_extensions import ParamSpec

T = TypeVar("T")
TParam = ParamSpec("TParam")


def escape_md(txt: str, ignores: Optional[Iterable] = None):
    # fmt:off
    chars = [
        "[", "]", "(", ")", "{", "}", "_", "*", "~", "`", ">", "#", "+", "-", "=", "|",
        ".", "!",
    ]
    # fmt:on
    for c in chars:
        if ignores and (c in ignores):
            continue
        txt = txt.replace(c, f"\\{c}")
    return txt


async def async_wrapper(
    origin_func: Callable[TParam, T],
    *args: TParam.args,
    **kwargs: TParam.kwargs,
) -> T:
    """异步调用包装"""
    return await awaitable(origin_func)(*args, **kwargs)  # type: ignore  # noqa: PGH003


def get_timestamp():
    return round(time.time() * 1000)
