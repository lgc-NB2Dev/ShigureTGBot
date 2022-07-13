import asyncio
import math
import random
import string
from html import escape

from nonebot import on
from nonebot.adapters.telegram import Message, Bot
from nonebot.adapters.telegram.event import MessageEvent, CallbackQueryEvent
from nonebot.adapters.telegram.exception import NetworkError
from nonebot.adapters.telegram.model import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .data_source import *
from ..base.cmd import on_command
from ..base.const import LINE_SEP

asyncio.get_event_loop().run_until_complete(login())

tmp_search = {}


def get_random_str(length: int = 6):
    return "".join(random.sample(f"{string.ascii_letters}{string.digits}", length))


@on_command("netease", "网易云音乐点歌").handle()
async def _(
    bot: Bot, matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()
):
    arg = arg.extract_plain_text().strip()
    if not arg:
        logged_in = GetCurrentSession().login_info["success"]
        login_warn = "警告！帐号未登录，功能将会受到限制\n" if not logged_in else ""
        return await matcher.finish(
            f"{login_warn}"
            "用法：/netease <歌曲名>\n"
            "可以听需要会员的歌曲（黑胶为自费）\n"
            "球球给点吃的吧~ → /about",
            reply_to_message_id=event.message_id,
        )

    msg_id = (await matcher.send("搜索中……", reply_to_message_id=event.message_id))[
        "result"
    ]["message_id"]

    tmp_search[salt := get_random_str()] = arg
    await edit_search_music_msg(bot, msg_id, event.chat.id, salt)


async def edit_search_music_msg(bot, msg_id, chat_id, salt, page=1):
    async def edit_message_text(text, **kwargs):
        return await bot.edit_message_text(
            text=text, message_id=msg_id, chat_id=chat_id, **kwargs
        )

    async def edit_message_reply_markup(markup=None):
        return await bot.edit_message_reply_markup(
            reply_markup=markup, message_id=msg_id, chat_id=chat_id
        )

    arg = tmp_search[salt]
    try:
        ret = await search(arg, page=page)
    except:
        logger.exception("歌曲搜索失败")
        return await edit_message_text("歌曲搜索失败，请重试")

    if ret["code"] != 200:
        return await edit_message_text(f'未知错误({ret["code"]})')

    ret = ret["result"]
    if not ret["songs"]:
        return await edit_message_text("未搜索到歌曲")

    inline_buttons = []
    tmp_row = []
    music_li = []
    row_width = 5
    limit = config.netease_list_limit
    max_page = math.ceil(ret["songCount"] / limit)

    for i, song in enumerate(ret["songs"]):
        alia = f'<i>（{escape("、".join(song["alia"]))}）</i>' if song["alia"] else ""
        ars = "、".join([escape(x["name"]) for x in song["ar"]])

        num = (limit * (page - 1)) + i + 1
        music_li.append(f'{num}. <b>{song["name"]}</b>{alia} - {ars}')
        tmp_row.append(
            InlineKeyboardButton(
                text=str(num), callback_data=f'netease|music|get|{song["id"]}'
            )
        )

        if len(tmp_row) == row_width or i == limit - 1:
            inline_buttons.append(tmp_row.copy())
            tmp_row.clear()

    if not page - 1 == 0:
        tmp_row.append(
            InlineKeyboardButton(
                text="< 上一页", callback_data=f"netease|music|page|{salt}|{page - 1}"
            )
        )
    if not page == max_page:
        tmp_row.append(
            InlineKeyboardButton(
                text="下一页 >", callback_data=f"netease|music|page|{salt}|{page + 1}"
            )
        )
    inline_buttons.append(tmp_row.copy())
    tmp_row.clear()

    music_li = "\n".join(music_li)
    msg = (
        f"【<b>{arg}</b>】的搜索结果：\n"
        f"{LINE_SEP}\n"
        f"{music_li}\n"
        f"{LINE_SEP}\n"
        f"第 <b>{page}</b> / <b>{max_page}</b> 页"
    )

    await edit_message_text(msg, parse_mode="HTML")
    await edit_message_reply_markup(
        InlineKeyboardMarkup(inline_keyboard=inline_buttons)
    )


async def get_music(bot: Bot, music_id, msg_id, chat_id):
    async def edit_message_text(text, **kwargs):
        return await bot.edit_message_text(
            text=text, message_id=msg_id, chat_id=chat_id, **kwargs
        )

    async def edit_message_reply_markup(markup_=None):
        return await bot.edit_message_reply_markup(
            reply_markup=markup_, message_id=msg_id, chat_id=chat_id
        )

    await edit_message_reply_markup(InlineKeyboardMarkup(inline_keyboard=[]))

    # 获取歌曲信息
    await edit_message_text("获取歌曲详细信息中……")
    try:
        ret_info = await get_track_info([music_id])
    except:
        logger.exception("获取歌曲详细信息失败")
        return await edit_message_text("获取歌曲详细信息失败，请重试")

    if ret_info["code"] != 200:
        return await edit_message_text(f'未知错误({ret_info["code"]})')

    if not ret_info["songs"]:
        return await edit_message_text("未找到歌曲")
    info_song = ret_info["songs"][0]
    info_privilege = ret_info["privileges"][0]

    # 获取歌曲下载链接
    await edit_message_text("获取歌曲下载链接中……")
    try:
        ret_down = await get_track_audio(
            [int(music_id)], bit_rate=info_privilege["maxbr"]
        )
    except:
        logger.exception("获取歌曲下载链接失败")
        return await edit_message_text("获取歌曲下载链接失败，请重试")

    if ret_down["code"] != 200:
        return await edit_message_text(f'未知错误({ret_down["code"]})')

    ret_down = ret_down["data"]
    if (not ret_down) or (not ret_down[0]["url"]):
        return await edit_message_text("未找到歌曲/歌曲没有下载链接")
    info_down = ret_down[0]

    # 处理
    msg = "\n".join(
        [
            f'《<b>{escape(info_song["name"])}</b>》',
            "\n".join([f"<i>{escape(x)}</i>" for x in info_song["alia"]]),
            "\n",
            ("<i>注：由于nonebot-adapter-telegram的一个问题，" "下面的按钮点击是没反应的，等bug修了再接着做</i>"),
            "\n",
            "via @shiguretgbot",
        ]
    )
    buttons = []
    for ar in info_song["ar"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f'歌手：{ar["name"]}', callback_data=f'netease|ar|{ar["id"]}|1'
                )
            ]
        )
    al = info_song["al"]
    buttons.append(
        [
            InlineKeyboardButton(
                text=f'专辑：{al["name"]}', callback_data=f'netease|al|{al["id"]}|1'
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="歌词", callback_data=f"netease|music|lrc|{music_id}|1"
            ),
            InlineKeyboardButton(
                text="评论", callback_data=f"netease|music|comment|{music_id}|1"
            ),
        ]
    )

    if info_down["size"] > 20 * 1024 * 1024:  # 大于20M
        msg += f'\n文件超过20MB，无法上传，请点击<a href="{info_down["url"]}">这里</a>收听'
    else:
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        try:
            await edit_message_text("上传文件中……")

            await bot.send_audio(
                thumb=info_song["al"]["picUrl"],
                audio=info_down["url"],
                chat_id=chat_id,
                reply_markup=markup,
                title=info_song["name"],
                caption=msg,
                parse_mode="HTML",
                performer="、".join([x["name"] for x in info_song["ar"]]),
            )
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except NetworkError as e:
            logger.opt(exception=e).exception("文件上传失败")
            msg += f'\n文件上传失败，请点击<a href="{info_down["url"]}">这里</a>收听'
            await edit_message_text(msg, parse_mode="HTML")
            await edit_message_reply_markup(markup)


def inline_rule(event: CallbackQueryEvent, state: T_State):
    data = event.data.split("|")
    state["data"] = data
    if data[0] == "netease":
        return True


@on("", rule=inline_rule).handle()
async def _(bot: Bot, event: CallbackQueryEvent, state: T_State):
    async def process():
        data = state["data"]
        match data[1]:
            case "music":

                match data[2]:
                    case "page":
                        await edit_search_music_msg(
                            bot,
                            event.message.message_id,
                            event.message.chat.id,
                            data[3],
                            int(data[4]),
                        )
                        return 1
                    case "get":
                        await get_music(
                            bot,
                            int(data[3]),
                            event.message.message_id,
                            event.message.chat.id,
                        )
                        return 1

    if not (await process()):
        await bot.answer_callback_query(callback_query_id=event.id, text="待更新")
    else:
        await bot.answer_callback_query(callback_query_id=event.id)
