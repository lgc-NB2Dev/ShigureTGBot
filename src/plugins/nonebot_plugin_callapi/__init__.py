from nonebot.plugin import PluginMetadata

from .__main__ import HELP_TEXT
from .config import ConfigModel

__version__ = "0.1.0"
__plugin_meta__ = PluginMetadata(
    "CallAPI",
    "使用指令来调用 Bot 的 API",
    HELP_TEXT,
    ConfigModel,
    {"License": "MIT", "Author": "student_2333"},
)
