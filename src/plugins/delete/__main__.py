from typing import cast

from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.adapters.telegram.model import User
from nonebot.log import logger
from nonebot.matcher import Matcher

from ..base.cmd import on_command

cmd_del = on_command("del", "自助删除消息", aliases={"delete", "revoke"})


@cmd_del.handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent):
    if not event.reply_to_message:
        await matcher.finish("请回复你希望我删除的消息", reply_to_message_id=event.message_id)

    # print(event.reply_to_message.dict())
    reply_user = cast(
        User | None,
        getattr(event.reply_to_message, "from_"),  # noqa: B009
    )
    if (not reply_user) or str(reply_user.id) != bot.self_id:
        # 怪，这里用 matcher 发不了消息
        await bot.send_message(
            text="我是不会删掉别人的消息的！！",
            chat_id=event.chat.id,
            reply_to_message_id=event.message_id,
        )
        return

    try:
        await bot.delete_message(
            chat_id=event.chat.id,
            message_id=event.reply_to_message.message_id,
        )
    except:
        logger.exception("删除消息失败")
        await matcher.finish("抱歉，删除失败", reply_to_message_id=event.message_id)
