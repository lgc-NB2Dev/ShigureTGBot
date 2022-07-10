"""
插件使用本插件注册命令，本插件自动将命令设置到Bot菜单
"""
from nonebot import get_driver
from nonebot import on_command as raw_on_command
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.model import BotCommand

command_list = []


def on_command(cmd: str | tuple, desc: str, *args, **kwargs):
    command_list.append(BotCommand(command=cmd, description=desc))
    return raw_on_command(cmd, *args, **kwargs)


@get_driver().on_bot_connect
async def _(bot: Bot):
    await bot.set_my_commands(commands=command_list)
