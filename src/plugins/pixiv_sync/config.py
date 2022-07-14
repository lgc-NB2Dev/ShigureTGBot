from pathlib import Path
from typing import Optional

from nonebot import get_driver
from pydantic import BaseSettings

from ..data import PluginData


class Config(BaseSettings):
    pixiv_oauth_user: Optional[int] = None
    pixiv_sync_to_chats: list[int] = None
    pixiv_sync_delay: int = 300

    class Config:
        extra = "ignore"


global_config = get_driver().config
config = Config.parse_obj(global_config)

data = PluginData(Path(__file__).parent.name)
