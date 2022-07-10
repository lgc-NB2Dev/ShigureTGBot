from nonebot import get_driver
from pydantic import BaseSettings


class Config(BaseSettings):
    netease_phone: str | int = None
    netease_pwd: str = None
    netease_list_limit: int = 10

    class Config:
        extra = "ignore"


global_config = get_driver().config
config = Config.parse_obj(global_config)
