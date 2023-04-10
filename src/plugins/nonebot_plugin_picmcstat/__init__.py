from nonebot.plugin import PluginMetadata

from . import __main__ as __main__

__plugin_meta__ = PluginMetadata(
    name="PicMCStat",
    description="将一个 Minecraft 服务器的 MOTD 信息绘制为一张图片",
    usage="使用 motd 指令查看使用帮助",
)

__version__ = "0.3.0"
