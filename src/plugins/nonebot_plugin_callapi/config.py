from nonebot import get_driver
from pydantic import BaseModel


class ConfigModel(BaseModel):
    callapi_pic: bool = True


config: ConfigModel = ConfigModel.parse_obj(get_driver().config.dict())
