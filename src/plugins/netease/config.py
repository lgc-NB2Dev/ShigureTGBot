from pathlib import Path
from typing import Optional

from nonebot import get_driver
from pydantic import BaseSettings

from ..data import PluginData


class Config(BaseSettings):
    superusers: list[int]

    netease_phone: Optional[str] = None
    netease_pwd: Optional[str] = None
    netease_list_limit: int = 10
    netease_login: bool = True
    netease_fake_ip: bool | str = False
    netease_ct_code: int = 86
    netease_ignore_size: bool = False

    class Config:
        extra = "ignore"


global_config = get_driver().config
config = Config.parse_obj(global_config)

data = PluginData(Path(__file__).parent.name)
session = PluginData(Path(__file__).parent.name, "session.json")
