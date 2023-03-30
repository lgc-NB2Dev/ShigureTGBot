from io import BytesIO

from nonebot import logger
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.adapters.telegram.message import File
from nonebot.internal.adapter import Message
from nonebot.internal.matcher import Matcher
from PIL import Image

from ..base.cmd import CommandArg, on_command
from .config import config
from .draw import get_stat_pic
from .util import download_file

# def trigger_rule():
#     def check_su(event: MessageEvent):
#         if config.ps_only_su:
#             return event.get_user_id() in config.superusers
#         return True

#     def check_empty_arg(arg: Message = CommandArg()):
#         return not arg.extract_plain_text()

#     checkers = [check_su, check_empty_arg]
#     if config.ps_need_at:
#         checkers.append(ToMeRule())

#     return Rule(*checkers)


stat_matcher = on_command("status", "查看 Bot 运行状态", aliases={"stat"})


@stat_matcher.handle()
async def _(
    bot: Bot,
    event: MessageEvent,
    matcher: Matcher,
    arg: Message = CommandArg(),
):
    msg = event.message
    if event.reply_to_message and event.reply_to_message.message:
        msg += event.reply_to_message.message

    file_id = None
    if photos := msg["photo"]:
        file_id = photos[0].data["file"]

    elif documents := msg["document"]:
        for doc in msg["document"]:
            data = doc.data["document"]
            if data["mime_type"].startswith("image/"):
                if data["file_size"] > 15728640:
                    await matcher.send(
                        "背景图需要<=15MB，忽略自定义背景图",
                        reply_to_message_id=event.message_id,
                    )
                else:
                    file_id = data["file_id"]
                break

    pic = Image.open(BytesIO(await download_file(bot, file_id))) if file_id else None

    try:
        ret = await get_stat_pic(bot, pic)
    except:
        logger.exception("获取运行状态图失败")
        return await matcher.finish(
            "获取运行状态图片失败，请检查后台输出",
            reply_to_message_id=event.message_id,
        )

    await matcher.finish(File.photo(ret), reply_to_message_id=event.message_id)
