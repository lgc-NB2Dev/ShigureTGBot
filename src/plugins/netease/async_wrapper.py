"""
异步调用包装
https://zhuanlan.zhihu.com/p/56927974
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor


class AsyncWrapper:
    def __init__(self, loop=None, max_workers=None):
        self.loop = loop or asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def run(self, origin_func, *args, **kwargs):
        def wrapper_():
            return origin_func(*args, **kwargs)

        return await self.loop.run_in_executor(self.executor, wrapper_)


wrapper = AsyncWrapper()
