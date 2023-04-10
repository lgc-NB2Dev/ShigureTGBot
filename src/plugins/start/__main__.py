from nonebot.adapters.telegram.event import MessageEvent
from nonebot.matcher import Matcher

from ..base.cmd import on_command

cmd_start = on_command("start", "开始调教Shigure♡")


@cmd_start.handle()
async def _(matcher: Matcher, event: MessageEvent):
    await matcher.send(
        "你好~我是Shigure~\n目前Bot功能正在持续开发中，不妨看看命令菜单（/menu）都有些啥吧！",
        reply_to_message_id=event.message_id,
    )
