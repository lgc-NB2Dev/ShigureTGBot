import random

from nonebot.matcher import Matcher
from nonebot.params import CommandArg, Arg

from nonebot.adapters.telegram.event import MessageEvent
from nonebot.internal.adapter import Message
from nonebot.plugin import PluginMetadata

from .data import DATA
from ..base.cmd import on_command

__plugin_meta__ = PluginMetadata(
    name="发病语录",
    description="随机返回一条发病语录",
    usage="命令：发病 [发病对象]\n例如：发病 测试",
)

catch_str = on_command("genelec", "随机发癫语录")


@catch_str.handle()
async def _(matcher: Matcher, arg: Message = CommandArg()):
    if arg.extract_plain_text().strip():
        matcher.set_arg("target", arg)


@catch_str.got("target", "你要对哪个人发病呢？")
async def _(event: MessageEvent, matcher: Matcher, target: Message = Arg("target")):
    target_str = target.extract_plain_text().strip()
    if not target_str:
        await matcher.reject("你发的消息中没有文本，请重新输入！")

    msg = random.choice(DATA).format(target_name=target_str)
    await matcher.finish(msg, reply_to_message_id=event.message_id)
