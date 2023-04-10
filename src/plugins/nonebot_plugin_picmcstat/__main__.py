from typing import Awaitable, Callable, NoReturn

from nonebot import on_regex
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.internal.adapter import Message
from nonebot.matcher import Matcher

from ..base.cmd import CommandArg, on_command
from .config import ShortcutType, config
from .draw import ServerType, draw

motd_handler = on_command("motd", "获取 Minecraft 服务器信息")


@motd_handler.handle()
async def _(matcher: Matcher, event: MessageEvent, msg_arg: Message = CommandArg()):
    arg: str = msg_arg.extract_plain_text()

    svr_type: ServerType = "je"
    be_svr_prefix = ["pe", "be"]
    for p in be_svr_prefix:
        if arg.startswith(p):
            arg = arg.replace(p, "", 1)
            svr_type = "be"
            break

    arg = arg.strip()
    await matcher.finish(
        await draw(arg, svr_type),
        reply_to_message_id=event.message_id,
    )


def get_shortcut_handler(
    host: str,
    svr_type: ServerType,
) -> Callable[..., Awaitable[NoReturn]]:
    async def shortcut_handler(matcher: Matcher):
        await matcher.finish(await draw(host, svr_type))

    return shortcut_handler


def append_shortcut_handler(shortcut: ShortcutType):
    async def rule(event: MessageEvent):
        if wl := shortcut.whitelist:
            return event.chat.id in wl
        return True

    on_regex(shortcut.regex, rule=rule).append_handler(
        get_shortcut_handler(shortcut.host, shortcut.type),
    )


def startup():
    if s := config.mcstat_shortcuts:
        for v in s:
            append_shortcut_handler(v)


startup()
