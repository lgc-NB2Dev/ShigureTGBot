from pathlib import Path

from nonebot import get_driver
from pydantic import BaseModel, Extra


class PluginConfig(BaseModel, extra=Extra.ignore):
    crazy_path: Path = Path(__file__).parent


driver = get_driver()
crazy_config: PluginConfig = PluginConfig.parse_obj(driver.config.dict())
