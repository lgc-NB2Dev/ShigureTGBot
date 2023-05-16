import asyncio
import math
import random
import string
from html import escape
from typing import Any, Optional

from aiohttp import ClientSession
from nonebot import on
from nonebot.adapters.telegram import Bot, Message
from nonebot.adapters.telegram.event import CallbackQueryEvent, MessageEvent
from nonebot.adapters.telegram.exception import NetworkError
from nonebot.adapters.telegram.model import InlineKeyboardButton, InlineKeyboardMarkup
from nonebot.adapters.telegram.model import Message as MessageModel
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from ..base.cmd import CommandArg, on_command
from ..base.const import LINE_SEP
from ..base.rule import inline_rule
from .config import config, data, lyric
from .data_source import (
    GetCurrentSession,
    get_track_audio,
    get_track_info,
    get_track_lrc,
    login,
    search,
)
from .lrc_parser import merge, parse

asyncio.get_event_loop().run_until_complete(login())

tmp_search = {}


def get_random_str(length: int = 6):
    return "".join(random.sample(f"{string.ascii_letters}{string.digits}", length))


cmd_netease = on_command("netease", "网易云音乐点歌")


@cmd_netease.handle()
async def _(
    bot: Bot,
    matcher: Matcher,
    event: MessageEvent,
    arg: Message = CommandArg(),
):
    str_arg = arg.extract_plain_text().strip()
    if not str_arg:
        logged_in = GetCurrentSession().login_info["success"]
        login_warn = "警告！帐号未登录，功能将会受到限制\n" if not logged_in else ""
        await matcher.finish(
            f"{login_warn}"
            "用法：/netease <歌曲名>\n"
            "可以听需要会员的歌曲（黑胶为自费）\n"
            "球球给点吃的吧~ → /about",
            reply_to_message_id=event.message_id,
        )

    is_id = str_arg.isdigit()
    msg_sent: MessageModel = await matcher.send(
        "检测到输入了歌曲 ID，直接寻找对应歌曲……" if is_id else "搜索中……",
        reply_to_message_id=event.message_id,
    )
    msg_id = msg_sent.message_id

    if is_id:
        await get_music(bot, str_arg, msg_id, event.chat.id, None)

    else:
        tmp_search[salt := get_random_str()] = str_arg
        await edit_search_music_msg(bot, msg_id, event.chat.id, salt)


async def edit_search_music_msg(bot, msg_id, chat_id, salt, page=1):
    async def edit_message_text(text, **kwargs):
        return await bot.edit_message_text(
            text=text,
            message_id=msg_id,
            chat_id=chat_id,
            **kwargs,
        )

    arg = tmp_search[salt]
    try:
        ret = await search(arg, page=page)
        # print(ret)
    except:
        logger.exception("歌曲搜索失败")
        return await edit_message_text("歌曲搜索失败，请重试")

    # if ret["code"] != 200:
    #     return await edit_message_text(f'未知错误({ret["code"]})')

    ret = ret["result"]
    if not (ret and ret.get("songs")):
        return await edit_message_text("未搜索到歌曲 / 搜索出错")

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
                text=str(num),
                callback_data=f'netease|music|get|{song["id"]}',
            ),
        )

        if len(tmp_row) == row_width or i == limit - 1:
            inline_buttons.append(tmp_row.copy())
            tmp_row.clear()

    if page != 1:
        tmp_row.append(
            InlineKeyboardButton(
                text="< 上一页",
                callback_data=f"netease|music|page|{salt}|{page - 1}",
            ),
        )
    if page != max_page:
        tmp_row.append(
            InlineKeyboardButton(
                text="下一页 >",
                callback_data=f"netease|music|page|{salt}|{page + 1}",
            ),
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

    await edit_message_text(
        msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_buttons),
    )
    return None


async def get_music(bot: Bot, music_id, msg_id, chat_id, reply_to_id):
    async def edit_message_text(text, **kwargs):
        return await bot.edit_message_text(
            text=text,
            message_id=msg_id,
            chat_id=chat_id,
            **kwargs,
        )

    # 获取歌曲信息
    await edit_message_text(
        "获取歌曲详细信息中……",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
    )
    try:
        ret_info = await get_track_info([music_id])
    except:
        logger.exception("获取歌曲详细信息失败")
        await edit_message_text("获取歌曲详细信息失败，请重试")
        return

    if ret_info["code"] != 200:
        await edit_message_text(f'未知错误({ret_info["code"]})')
        return

    if not ret_info["songs"]:
        await edit_message_text("未找到歌曲")
        return
    info_song = ret_info["songs"][0]
    info_privilege = ret_info["privileges"][0]

    song_name = info_song["name"]
    performer = "、".join([x["name"] for x in info_song["ar"]])

    too_large = False
    cached_file = data.get(str(music_id))
    if cached_file:
        audio_url = f"https://music.163.com/#/song?id={music_id}"
        audio_file = cached_file
    else:
        # 获取歌曲下载链接
        await edit_message_text("获取歌曲下载链接中……")
        try:
            ret_down = await get_track_audio(
                [int(music_id)],
                bit_rate=info_privilege["maxbr"],
            )
        except:
            logger.exception("获取歌曲下载链接失败")
            await edit_message_text("获取歌曲下载链接失败，请重试")
            return

        if ret_down["code"] != 200:
            await edit_message_text(f'未知错误({ret_down["code"]})')
            return

        ret_down = ret_down["data"]
        if (not ret_down) or (not ret_down[0]["url"]):
            await edit_message_text("未找到歌曲/歌曲没有下载链接")
            return

        info_down = ret_down[0]
        audio_url = info_down["url"]

        # 处理
        await edit_message_text("下载歌曲中……")
        too_large: bool = (
            False
            if config.netease_ignore_size
            else info_down["size"] > 50 * 1024 * 1024
        )
        if not too_large:
            try:
                async with ClientSession() as s:
                    async with s.get(audio_url) as r:
                        audio_file = await r.read()
            except:
                logger.exception("下载歌曲失败")
                await edit_message_text("抱歉……下载歌曲失败，请稍后重试！")
                return
        else:
            audio_file = None

    await edit_message_text("下载封面中……")
    thumbnail = None
    try:
        async with ClientSession() as s:
            async with s.get(
                info_song["al"]["picUrl"],
                params={"imageView": "", "thumbnail": "320y320", "type": "jpeg"},
            ) as r:
                thumbnail = await r.read()
    except:
        logger.exception("下载封面失败")

    msg = []
    if not thumbnail:
        msg.append("<i>歌曲封面下载失败</i>\n")

    msg.append(f'<b>{escape(info_song["name"])}</b> - {escape(performer)}')

    if alia := info_song["alia"]:
        msg.append("")
        msg.append("\n".join([f"<i>{escape(x)}</i>" for x in alia]))

    if not audio_file:
        msg.append(f'\n文件超过50MB，无法上传，请点击<a href="{audio_url}">这里</a>收听')

    msg.append("\nvia @shiguretgbot")
    msg = "\n".join(msg)

    buttons = []
    for ar in info_song["ar"]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f'歌手：{ar["name"]}',
                    url=f'https://music.163.com/#/artist?id={ar["id"]}',
                    # callback_data=f'netease|ar|{ar["id"]}|1',
                ),
            ],
        )
    al = info_song["al"]
    buttons.append(
        [
            InlineKeyboardButton(
                text=f'专辑：{al["name"]}',
                url=f'https://music.163.com/#/album?id={al["id"]}',
                # callback_data=f'netease|al|{al["id"]}|1',
            ),
        ],
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="歌词",
                callback_data=f"netease|music|lrc|{music_id}|1",
            ),
            InlineKeyboardButton(
                text="评论",
                callback_data=f"netease|music|comment|{music_id}|1",
            ),
        ],
    )
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    if not audio_file:
        await edit_message_text(msg, parse_mode="HTML", reply_markup=markup)
        return

    try:
        await edit_message_text("命中本地缓存，正在发送……" if cached_file else "上传文件中……")
        ret = (
            await bot.send_audio(
                thumbnail=thumbnail,
                audio=audio_file,
                chat_id=chat_id,
                reply_markup=markup,
                title=song_name,
                caption=msg,
                parse_mode="HTML",
                performer=performer,
                reply_to_message_id=reply_to_id,
            )
        ).audio.file_id  # type: ignore  # noqa: PGH003
        await data.set(str(music_id), ret)
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except NetworkError as e:
        logger.opt(exception=e).exception("文件上传失败")
        msg += f'\n文件上传失败，请点击<a href="{audio_url}">这里</a>收听'


def parse_lrc(lrc: dict[str, Any]) -> str:
    def fmt_usr(usr: dict[str, Any]) -> str:
        return f'<a href="https://music.163.com/#/user/home?id={usr["userid"]}">{escape(usr["nickname"])}</a>'

    raw = lrc.get("lrc")
    if (not raw) or (not (raw_lrc := raw["lyric"])):
        return "该歌曲没有歌词"

    lrcs = [
        parse(x["lyric"])
        for x in [
            raw,
            lrc.get("romalrc"),
            lrc.get("tlyric"),
        ]
        if x
    ]
    lrcs = [x for x in lrcs if x]

    lines = []
    if not lrcs:
        lines.append("<i>该歌曲没有滚动歌词</i>")
        lines.append("")
        lines.append("--------")
        lines.append("")
        lines.append(raw_lrc)
    else:
        only_one = len(lrcs) == 1
        for li in merge(*lrcs):
            if not only_one:
                lines.append("")
            lines.append(f"<b>{escape(li[0].lrc)}</b>")
            lines.extend([f"{escape(x.lrc)}" for x in li[1:]])

    lrc_user = lrc.get("lyricUser")
    trans_user = lrc.get("transUser")
    if lrc_user or trans_user:
        lines.append("")
        lines.append("--------")
        lines.append("")

        if lrc_user:
            lines.append(f"歌词贡献者：{fmt_usr(lrc_user)}")
        if trans_user:
            lines.append(f"翻译贡献者：{fmt_usr(trans_user)}")

    return "\n".join(lines).strip()


async def music_lrc(
    bot: Bot,
    msg_id: Optional[int],
    chat_id: int,
    reply_to: Optional[int],
    music_id: str,
    _: int,  # page
):
    async def send_message(text: str, **kwargs):
        nonlocal msg_id

        if msg_id:
            return await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=msg_id,
                **kwargs,
            )

        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=reply_to,
            **kwargs,
        )
        msg_id = msg.message_id
        return msg

    try:
        lrc: str | None = lyric.get(music_id)
        if not lrc:
            lrc = parse_lrc(await get_track_lrc(music_id))
            await lyric.set(music_id, lrc)
    except:
        logger.exception("获取歌词失败")
        await send_message("获取歌词失败")
        return

    await send_message(lrc, parse_mode="HTML", disable_web_page_preview=True)


inline_netease = on("", rule=inline_rule("netease"))


@inline_netease.handle()
async def _(bot: Bot, event: CallbackQueryEvent, state: T_State):
    if not event.message:
        return

    reply_to = (
        event.message.reply_to_message.message_id
        if event.message.reply_to_message
        else None
    )

    s_data: list[str] = state["data"]
    sub1 = s_data[1]
    if sub1 == "music":
        sub2 = s_data[2]
        if sub2 == "page":
            await edit_search_music_msg(
                bot,
                event.message.message_id,
                event.message.chat.id,
                s_data[3],
                int(s_data[4]),
            )
            return

        if sub2 == "get":
            await get_music(
                bot,
                int(s_data[3]),
                event.message.message_id,
                event.message.chat.id,
                reply_to,
            )
            return

        if sub2 == "lrc":
            await bot.answer_callback_query(callback_query_id=event.id)
            await music_lrc(
                bot,
                None,  # new msg
                event.message.chat.id,
                event.message.message_id,
                s_data[3],
                int(s_data[4]),
            )
            return

        if sub2 == "comment":
            await bot.answer_callback_query(callback_query_id=event.id, text="待更新")
            return

    # await bot.answer_callback_query(callback_query_id=event.id, text="待更新")


cmd_relogin = on_command("netease_relogin", "网易云重登", hide=True, permission=SUPERUSER)


@cmd_relogin.handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent):
    msg_sent: MessageModel = await matcher.send(
        "重新登录中……",
        reply_to_message_id=event.message_id,
    )
    msg_id = msg_sent.message_id

    ret = await login(bot, event.chat.id)
    if isinstance(ret, Exception):
        return await bot.edit_message_text(
            chat_id=event.chat.id,
            message_id=msg_id,
            text=f"登录失败\n{ret!r}",
        )
    await bot.edit_message_text(chat_id=event.chat.id, message_id=msg_id, text="登录成功")
    return None
