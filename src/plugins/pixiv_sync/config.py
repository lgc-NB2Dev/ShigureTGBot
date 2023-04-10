from pathlib import Path
from typing import Optional

from nonebot import get_driver
from pydantic import BaseSettings

from ..data import PluginData


class Config(BaseSettings):
    pixiv_sync_to_chats: list[int] = []
    pixiv_sync_delay: int = 3600
    pixiv_send_delay: int = 10

    telegram_proxy: Optional[str] = None
    superusers: list[int]

    class Config:
        extra = "ignore"


global_config = get_driver().config
config = Config.parse_obj(global_config)

data = PluginData(Path(__file__).parent.name)
