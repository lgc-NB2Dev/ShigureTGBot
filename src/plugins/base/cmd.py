"""
插件使用本插件注册命令，本插件自动将命令设置到Bot菜单
"""
from nonebot import get_driver, logger
from nonebot import on_command as raw_on_command
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.adapters.telegram.model import BotCommand
from nonebot.matcher import Matcher

command_list = []


def on_command(cmd: str | tuple, desc: str, *args, **kwargs):
    command_list.append(BotCommand(command=cmd, description=desc))
    return raw_on_command(cmd, *args, **kwargs)


def get_cmd_list_txt():
    prefix = list(get_driver().config.command_start)[0]
    return "\n".join([f"{prefix}{x.command} - {x.description}" for x in command_list])


@get_driver().on_bot_connect
async def _(bot: Bot):
    command_list.sort(key=lambda x: x.command)

    logger.info(f"Bot {bot.self_id} connected")
    logger.info(f"Registered Commands:\n{get_cmd_list_txt()}")
    await bot.set_my_commands(commands=command_list)


@on_command("menu", "功能列表").handle()
async def _(matcher: Matcher, event: MessageEvent):
    await matcher.send(
        "Shigure☆功能列表\n" "-=-=-=-=-=-=-=-=-=-\n" f"{get_cmd_list_txt()}",
        reply_to_message_id=event.message_id,
    )
