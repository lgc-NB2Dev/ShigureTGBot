from pathlib import Path

from ..base.util import async_wrapper


class PluginCache:
    def __init__(self, name):
        real_path = Path(__file__).parent.parent.parent / "cache"
        if not real_path.exists():
            real_path.mkdir(parents=True)

        self.path: Path = real_path / name
        if not self.path.exists():
            self.path.write_bytes(b"")

    async def get_text(self):
        await async_wrapper(self.path.read_text, encoding="utf-8")

    async def get_bytes(self):
        await async_wrapper(self.path.read_bytes)

    async def set_text(self, data):
        await async_wrapper(self.path.write_text, data, encoding="utf-8")

    async def set_bytes(self, data):
        await async_wrapper(self.path.write_bytes, data)

    def get_abspath(self):
        return self.path.resolve()

    def get_path(self):
        return str(self.path)

    def __del__(self):
        self.path.unlink()
