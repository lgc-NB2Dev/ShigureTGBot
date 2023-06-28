import json
import random
from pathlib import Path
from typing import List

from nonebot import on_regex
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.internal.adapter.message import Message
from nonebot.matcher import Matcher
from nonebot.params import Depends, RegexStr

from ..base.cmd import CommandArg, on_command
from .config import crazy_config

__crazy_thursday_version__ = "v0.2.6"
__crazy_thursday_notes__ = f"""
KFC疯狂星期四 {__crazy_thursday_version__}
[疯狂星期X] 随机输出KFC疯狂星期四文案
[狂乱X曜日] 随机输出KFC疯狂星期四文案""".strip()

crazy_cmd = on_command("kfc", "随机输出KFC疯狂星期四文案")
crazy_cn = on_regex(pattern=r"^疯狂星期\S$", priority=15, block=False)
crazy_jp = on_regex(pattern=r"^狂乱\S曜日$", priority=15, block=False)


async def get_weekday_cn(arg: str = RegexStr()) -> str:
    return arg[-1].replace("天", "日")


async def get_weekday_jp(arg: str = RegexStr()) -> str:
    return arg[2]


@crazy_cn.handle()
async def _(
    event: MessageEvent,
    matcher: Matcher,
    weekday: str = Depends(get_weekday_cn),
):
    await matcher.finish(rnd_kfc(weekday), reply_to_message_id=event.message_id)


@crazy_jp.handle()
async def _(
    event: MessageEvent,
    matcher: Matcher,
    weekday: str = Depends(get_weekday_jp),
):
    await matcher.finish(rnd_kfc(weekday), reply_to_message_id=event.message_id)


@crazy_cmd.handle()
async def _(event: MessageEvent, matcher: Matcher, weekday: Message = CommandArg()):
    weekday_str = weekday.extract_plain_text().strip() or "四"
    await matcher.finish(rnd_kfc(weekday_str), reply_to_message_id=event.message_id)


def rnd_kfc(day: str) -> str:
    # jp en cn
    tb: List[str] = [
        "月",
        "Monday",
        "一",
        "火",
        "Tuesday",
        "二",
        "水",
        "Wednesday",
        "三",
        "木",
        "Thursday",
        "四",
        "金",
        "Friday",
        "五",
        "土",
        "Saturday",
        "六",
        "日",
        "Sunday",
        "日",
    ]
    if day not in tb:
        return "给个准确时间，OK?"

    # Get the weekday group index
    idx: int = int(tb.index(day) / 3) * 3

    # json数据存放路径
    path: Path = crazy_config.crazy_path / "post.json"

    # 将json对象加载到数组
    kfc = json.loads(path.read_text(encoding="u8")).get("post")

    # 随机选取数组中的一个对象，并替换日期
    return (
        random.choice(kfc)
        .replace("木曜日", tb[idx] + "曜日")
        .replace("Thursday", tb[idx + 1])
        .replace("thursday", tb[idx + 1])
        .replace("星期四", "星期" + tb[idx + 2])
        .replace("周四", "周" + tb[idx + 2])
        .replace("礼拜四", "礼拜" + tb[idx + 2])
    )
