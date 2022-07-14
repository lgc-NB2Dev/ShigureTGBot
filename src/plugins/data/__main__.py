import json
from pathlib import Path

from ..base.util import async_wrapper


class PluginData:
    def __init__(self, path, name='data.json'):
        real_path = Path(__file__).parent.parent.parent / 'data' / path
        if not real_path.exists():
            real_path.mkdir(parents=True)

        self.path: Path = real_path / name
        if not self.path.exists():
            self.path.write_text('{}')

        self.data: dict = {}
        self.refresh()

    def get(self, name, default=None):
        return self.data.get(name, default)

    async def set(self, name, value):
        self.data[name] = value
        await self.save()

    async def save(self):
        await async_wrapper(
            self.path.write_text,
            json.dumps(self.data)
        )

    def refresh(self):
        self.data = json.loads(self.path.read_text())
