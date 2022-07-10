"""
异步调用包装
https://zhuanlan.zhihu.com/p/56927974
"""

from awaits.awaitable import awaitable


async def wrapper(origin_func, *args, **kwargs):
    @awaitable
    def wrapper_():
        return origin_func(*args, **kwargs)

    return await wrapper_()
