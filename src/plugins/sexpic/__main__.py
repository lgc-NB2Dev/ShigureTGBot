from html import escape

import aiohttp
from nonebot import get_driver, logger, on
from nonebot.adapters.telegram import Bot, Message
from nonebot.adapters.telegram.event import CallbackQueryEvent, MessageEvent
from nonebot.adapters.telegram.model import InlineKeyboardButton, InlineKeyboardMarkup
from nonebot.params import RawCommand
from nonebot.typing import T_State

from ..base.cmd import CommandArg, on_command
from ..base.rule import inline_rule
from ..cache import PluginCache

config = get_driver().config


@on_command("sexpic_r18", "不够涩！！我要更涩的！！！").handle()
@on_command("sexpic", "涩图！我要涩涩！！").handle()
async def _(
    bot: Bot, event: MessageEvent, arg: Message = CommandArg(), cmd: str = RawCommand()
):
    await get_setu(
        bot,
        event.chat.id,
        arg.extract_plain_text().strip(),
        1 if (cmd == "/sexpic_r18") else 0,
        event.message_id,
    )


async def get_setu(bot, chat_id, arg, r18, reply_to=None):
    tag = [xx for x in arg.split(" ") if (xx := x.strip())]
    if len(tag) > 3:
        return await bot.send_message(
            chat_id=chat_id, text="and规则的tag匹配数不能超过3个", reply_to_message_id=reply_to
        )
    for i in tag:
        if len(i.split("|")) > 20:
            return await bot.send_message(
                chat_id=chat_id, text="or规则的tag匹配数不能超过20个", reply_to_message_id=reply_to
            )

    msg_id = (
        await bot.send_message(
            chat_id=chat_id, text="正在取得涩图信息~", reply_to_message_id=reply_to
        )
    )["result"]["message_id"]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.lolicon.app/setu/v2",
                json={"proxy": 0, "num": 1, "tag": tag, "r18": r18},
            ) as response:
                ret = await response.json()
    except:
        logger.exception("获取涩图URL失败")
        await bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text="啊呜……获取涩图信息失败惹……"
        )

    ret = ret["data"]
    if not ret:
        return await bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text="没有找到符合要求的图片捏"
        )
    ret = ret[0]

    search_tags = []
    for t in tag:
        search_tags.extend(t.split("|"))

    pic_tags = []
    for t in ret["tags"]:  # type:str
        find = False
        et = escape(t)
        for tt in search_tags:
            if t.find(tt) != -1:
                pic_tags.append(f"<b>{et}</b>")
                find = True
                break
        if not find:
            pic_tags.append(f"<code>{et}</code>")

    caption = (
        f"<b>奉上{'R18' if r18 else ''}涩图一张~</b>\n"
        f'PID：<code>{ret["pid"]}</code>\n'
        f'标题：<a href="https://www.pixiv.net/artworks/{ret["pid"]}">{escape(ret["title"])}</a>\n'
        f'作者：<a href="https://www.pixiv.net/users/{ret["uid"]}">{escape(ret["author"])}</a>\n'
        f'标签：{"；".join(pic_tags)}'
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="社保了！多来点！！" if r18 else "不够涩！我还要！！",
                    callback_data=f"sexpic|more|{' '.join(tag)}|{r18}",
                )
            ]
        ]
    )

    await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="下载涩图中……")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                ret["urls"]["original"],
                proxy=getattr(config, "telegram_proxy", None),
                timeout=aiohttp.ClientTimeout(total=60),
                headers={"referer": "https://www.pixiv.net/"},
            ) as response:
                pic = await response.read()
    except:
        logger.exception("获取涩图URL失败")
        return await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=f"<b>呜……图片下载失败……\n请试试看点击图片标题跳转到Pixiv查看</b>\n\n{caption}",
            reply_markup=markup,
            parse_mode="HTML",
        )

    await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text="上传涩图中……")

    try:
        cache = PluginCache(f'{ret["pid"]}_p{ret["p"]}.{ret["ext"]}')
        await cache.set_bytes(pic)
        await bot.send_document(
            chat_id=chat_id,
            document=cache.get_path(),
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup,
            reply_to_message_id=reply_to,
        )
    except:
        logger.exception("上传涩图失败")
        return await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=f"<b>呜……图片上传失败……\n请试试看点击图片标题跳转到Pixiv查看</b>\n\n{caption}",
            reply_markup=markup,
            parse_mode="HTML",
        )
    else:
        await bot.delete_message(message_id=msg_id, chat_id=chat_id)


@on("", rule=inline_rule("sexpic")).handle()
async def _(bot: Bot, event: CallbackQueryEvent, state: T_State):
    data = state["data"]
    arg = "|".join(data[2:-1])
    r18 = int(data[-1])
    await bot.answer_callback_query(callback_query_id=event.id)
    await get_setu(bot, event.message.chat.id, arg, r18, event.message.message_id)
