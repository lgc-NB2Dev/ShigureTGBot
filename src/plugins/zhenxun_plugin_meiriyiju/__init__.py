import random
from pathlib import Path

import nonebot
from nonebot.matcher import Matcher
from nonebot.internal.adapter import Message

from ..base.cmd import on_command, CommandArg

try:
    import ujson as json
except ModuleNotFoundError:
    import json


POST_JSON = json.loads(
    (Path(__file__).parent / "resource" / "post.json").read_text(encoding="u8")
)["post"]


aya = on_command("genelec", "随机发癫语录")


@aya.handle()
async def _(matcher: Matcher, arg: Message = CommandArg()):
    name = arg.extract_plain_text().strip()
    msg = random.choice(POST_JSON)
    if name:
        msg = msg.replace("阿咪", name)
    await matcher.finish(msg)
