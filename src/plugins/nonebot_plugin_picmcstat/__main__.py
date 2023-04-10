from typing import Awaitable, Callable, NoReturn

from nonebot import on_regex, require
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.internal.adapter import Message
from nonebot.matcher import Matcher

from ..base.cmd import CommandArg, on_command
from .config import config

require("nonebot_plugin_imageutils")

from .draw import ServerType, draw

motd_handler = on_command("motd", "获取 Minecraft 服务器信息", aliases={"!motd", "！motd"})


@motd_handler.handle()
async def _(matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()):
    arg = arg.extract_plain_text()

    svr_type: ServerType = "je"
    be_svr_prefix = ["pe", "be"]
    for p in be_svr_prefix:
        if arg.startswith(p):
            arg = arg.replace(p, "", 1)
            svr_type = "be"
            break

    arg = arg.strip()
    await matcher.finish(
        await draw(arg, svr_type), reply_to_message_id=event.message_id
    )


def get_shortcut_handler(
    host: str, svr_type: ServerType
) -> Callable[[...], Awaitable[NoReturn]]:
    async def shortcut_handler(matcher: Matcher, event: MessageEvent):
        await matcher.finish(
            await draw(host, svr_type), reply_to_message_id=event.message_id
        )

    return shortcut_handler


def startup():
    if s := config.mcstat_shortcuts:
        for shortcut in s:
            on_regex(shortcut["regex"]).append_handler(
                get_shortcut_handler(shortcut["host"], shortcut["type"])
            )


startup()
