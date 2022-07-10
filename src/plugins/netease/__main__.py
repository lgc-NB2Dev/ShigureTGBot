import math
import random
import string

from nonebot import on
from nonebot.adapters.telegram import Message, Bot
from nonebot.adapters.telegram.event import MessageEvent, CallbackQueryEvent
from nonebot.adapters.telegram.exception import NetworkError
from nonebot.adapters.telegram.model import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAudio,
)
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .data_source import *
from ..base.cmd import on_command
from ..base.const import LINE_SEP
from ..base.util import escape_md

tmp_search = {}


def get_random_str(length: int = 6):
    return "".join(random.sample(f"{string.ascii_letters}{string.digits}", length))


@on_command("netease", "网易云音乐点歌")
async def _(
    bot: Bot, matcher: Matcher, event: MessageEvent, arg: Message = CommandArg()
):
    arg = arg.extract_plain_text().strip()
    if not arg:
        return await matcher.finish(
            "用法：/netease <歌曲名>\n" "可以听需要会员的歌曲（黑胶为自费）\n" "球球给点吃的吧~ → /about",
            reply_to_message_id=event.message_id,
        )

    msg_id = (await matcher.send("搜索中……", reply_to_message_id=event.message_id))[
        "result"
    ]["message_id"]

    tmp_search[salt := get_random_str()] = arg
    await edit_search_music_msg(bot, msg_id, event.chat.id, salt)


async def edit_search_music_msg(bot, msg_id, chat_id, salt, page=1):
    arg = tmp_search[salt]
    try:
        ret = await search(arg, page=page)
    except:
        logger.exception("歌曲搜索失败")
        return bot.edit_message_text(
            text="歌曲搜索失败，请重试", message_id=msg_id, chat_id=chat_id
        )

    if ret["code"] != 200:
        return bot.edit_message_text(
            text=f'未知错误({ret["code"]})', message_id=msg_id, chat_id=chat_id
        )

    ret = ret["result"]
    if not ret["result"]["songs"]:
        return bot.edit_message_text(text="未搜索到歌曲", message_id=msg_id, chat_id=chat_id)

    inline_buttons = []
    tmp_row = []
    music_li = []
    row_width = 5
    limit = len(ret["songs"])
    max_page = math.ceil(ret["songCount"] / limit)

    for i, song in enumerate(ret["songs"]):
        alia = f'_（{"、".join(song["alia"])}）_' if song["alia"] else ""  # 斜体
        ars = "、".join([x["name"] for x in song["ar"]])

        num = (limit * (page - 1)) + 1
        music_li.append(f'{num}. *{song["name"]}*{alia} - {ars}')  # 曲名粗体
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
    sep = escape_md(LINE_SEP)
    msg = (
        f"【*{arg}*】的搜索结果：\n"  # 粗体
        f"{sep}\n"
        f"{music_li}\n"
        f"{sep}\n"
        f"第 *{page}* / *{max_page}* 页"
    )

    await bot.edit_message_text(text=msg, message_id=msg_id, chat_id=chat_id)
    await bot.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_buttons),
        message_id=msg_id,
        chat_id=chat_id,
    )


async def get_music(bot: Bot, music_id, msg_id, chat_id):
    async def edit_message_text(text):
        return await bot.edit_message_text(
            text=text, message_id=msg_id, chat_id=chat_id
        )

    async def edit_message_reply_markup(markup=None):
        return await bot.edit_message_reply_markup(
            reply_markup=markup, message_id=msg_id, chat_id=chat_id
        )

    # 获取歌曲信息
    await edit_message_reply_markup()

    try:
        ret_info = await get_track_info([int(music_id)])
    except:
        logger.exception("获取歌曲详细信息失败")
        return await edit_message_text("获取歌曲详细信息失败，请重试")

    if ret_info["code"] != 200:
        return await edit_message_text(f'未知错误({ret_info["code"]})')

    if not ret_info["songs"]:
        return await edit_message_text("未找到歌曲")
    info_song = ret_info["songs"][0]
    info_privilege = ret_info["privileges"]["0"]

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
    msg = [
        f'《*{escape_md(info_song["name"])}*》',
        "\n".join([f"_{escape_md(x)}_" for x in info_song["alia"]]),
    ]
    buttons = []
    for ar in info_song["ar"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f'歌手：{ar["name"]}', callback_data=f'netease|ar|{ar["id"]}|1'
                )
            ]
        )
    for al in info_song["al"]:
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
        msg += f'\n文件超过20MB，无法上传，请点击[这里]({info_down["url"]})收听'
    else:
        try:
            await bot.edit_message_media(
                media=InputMediaAudio(
                    thumb=info_song["al"]["picUrl"], media=info_down["url"]
                ),
                message_id=msg_id,
                chat_id=chat_id,
            )
        except NetworkError as e:
            logger.opt(exception=e).exception("文件上传失败")
            msg += f'\n文件上传失败，请点击[这里]({info_down["url"]})收听'
    await edit_message_text(msg)
    await edit_message_reply_markup(InlineKeyboardMarkup(inline_keyboard=buttons))


def inline_rule(event: CallbackQueryEvent, state: T_State):
    data = event.data.split("|")
    state["data"] = data
    if data[0] == "netease":
        return True


@on("", rule=inline_rule)
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
                            data[4],
                        )
                    case "get":
                        await get_music(
                            bot,
                            data[3],
                            event.message.message_id,
                            event.message.chat.id,
                        )

    callback_txt = ""
    if not process():
        callback_txt = "待更新"
    await bot.answer_callback_query(callback_query_id=event.id, text=callback_txt)