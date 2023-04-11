import asyncio
import random
import re
from html import escape
from typing import List, Optional, cast

from aiohttp import ClientSession
from nonebot import get_bot, get_driver, logger
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.adapters.telegram.model import InputMediaDocument
from nonebot.adapters.telegram.model import (
    Message as MessageModel,
)
from nonebot.matcher import Matcher
from nonebot.params import EventPlainText
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler

from ..base.cmd import on_command
from ..base.const import LINE_SEP
from ..cache import PluginCache
from .config import config, data
from .data_source import PixivAPI
from .util import split_list

driver = get_driver()

handler = on_command("pixiv_login", "Pixiv收藏夹同步登录", hide=True, permission=SUPERUSER)
sync_handler = on_command("pixiv_sync", "Pixiv收藏夹同步", hide=True, permission=SUPERUSER)

api = PixivAPI(proxy=config.telegram_proxy)
syncing = False


async def login_via_token():
    if (not api.refresh_token) and (t := data.get("refresh_token")):
        api.refresh_token = t

    try:
        ret = await api.login()
    except:
        logger.exception("使用 refresh_token 登录出错")
        raise

    await data.set("refresh_token", api.refresh_token)
    api.user_name = ret["user"]["name"]


@driver.on_bot_connect
async def _(bot: Bot):
    await sync(bot)


@handler.handle()
async def _1(bot: Bot, matcher: Matcher, event: MessageEvent, state: T_State):
    if api.refresh_token:
        msg_sent: MessageModel = await matcher.send("发现 refresh_token，尝试直接登录")
        msg_id = msg_sent.message_id

        try:
            await login_via_token()
        except Exception as e:
            await matcher.send(f"登录失败，使用正常流程登录\n{e!r}")
        else:
            return await bot.edit_message_text(
                chat_id=event.chat.id,
                message_id=msg_id,
                text=f"重登成功，欢迎你，{api.user_name}",
            )

    state["old_msg_id"] = (
        cast(
            MessageModel,
            await matcher.send(
                (
                    "[PixivSync] 请登录\n"
                    f'<a href="{await api.login_web_part1()}">登录链接</a>\n'
                    "请直接将Auth Token发给我\n"
                    f'<a href="https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362">登录教程</a>'
                ),
                parse_mode="HTML",
                reply_to_message_id=event.message_id,
                disable_web_page_preview=True,
            ),
        )
    ).message_id
    await matcher.pause()  # noqa: RET503


@handler.handle()
async def _2(
    bot: Bot,
    matcher: Matcher,
    state: T_State,
    event: MessageEvent,
    code: str = EventPlainText(),
):
    msg_sent: MessageModel = await matcher.send("登录中")
    msg_id = msg_sent.message_id
    await bot.delete_message(chat_id=event.chat.id, message_id=state["old_msg_id"])

    try:
        await api.login_web_part2(code.strip())
    except Exception as e:
        logger.opt(exception=e).exception("登录失败")
        await bot.edit_message_text(
            text=f"登录失败\n{e!r}",
            chat_id=event.chat.id,
            message_id=msg_id,
        )
        return await matcher.finish()

    await data.set("refresh_token", api.refresh_token)
    await bot.edit_message_text(
        text=f"登录成功\n欢迎，{api.user_name}",
        chat_id=event.chat.id,
        message_id=msg_id,
    )
    return None


@scheduler.scheduled_job("interval", seconds=config.pixiv_sync_delay)
async def _():
    await sync()


@sync_handler.handle()
async def _(bot: Bot, event: MessageEvent):
    await sync(bot, event.chat.id)


async def sync(bot_arg: Optional[Bot] = None, chat_id: Optional[int] = None):
    global syncing

    bot = bot_arg or cast(Bot, get_bot())
    if not chat_id:
        chat_id = config.superusers[0]

    if syncing:
        return await bot.send_message(chat_id=chat_id, text="已有同步进程运行中，请勿重复运行")

    syncing = True
    try:
        await _sync(bot, chat_id)
    except Exception as e:
        logger.opt(exception=e).exception("同步时出现意外错误")
        await bot.send_message(chat_id=chat_id, text=f"同步时出现意外错误\n{e!r}")
    finally:
        syncing = False


async def _sync(bot: Bot, _chat_id: int):
    _msg_id = (await bot.send_message(chat_id=_chat_id, text="尝试自动重登……")).message_id

    async def edit_message_text(text_):
        await bot.edit_message_text(text=text_, chat_id=_chat_id, message_id=_msg_id)

    try:
        await login_via_token()
    except Exception as e:
        return await edit_message_text(
            f"尝试重登失败！\n请使用 /pixiv_login 手动重登，之后可以使用 /pixiv_sync 手动同步\n{e!r}",
        )

    synced = cast(List[int], data.get(str(api.user_id), []))
    will_sync = []

    def add_will_sync(illusts_):
        will_add = []
        for it in illusts_:
            if it["id"] not in synced:
                will_add.append(it)

        if not will_add:
            return True
        will_sync.extend(will_add)
        return None

    max_bookmark_id = None
    i = 1
    while True:
        await edit_message_text(f"获取第 {i} 页收藏 | 已获取 {len(will_sync)}")
        bookmarks = await api.user_bookmarks_illust(
            api.user_id,
            max_bookmark_id=max_bookmark_id,  # type: ignore  # noqa: PGH003
        )
        logger.debug(f"bookmarks={bookmarks}")

        illusts = bookmarks["illusts"]
        if add_will_sync(illusts):
            break

        await asyncio.sleep(random.randint(1, 3))
        if not (
            (next_url := bookmarks["next_url"])
            and (max_bookmark_id := re.search("max_bookmark_id=([0-9]+)", next_url))
        ):
            break
        max_bookmark_id = max_bookmark_id.group(1)
        logger.debug(f"max_bookmark_id={max_bookmark_id}")
        i += 1

    will_sync.reverse()

    total = len(will_sync)
    if total == 0:
        return await edit_message_text("没有收藏可以同步")

    success = 0
    fail = 0
    for n, i in enumerate(will_sync):

        def get_tip():
            return f"正在发送 {n + 1} / {total}\n成功 {success}，失败 {fail}"  # noqa: B023

        await edit_message_text(get_tip())

        tags = []
        for x in i["tags"]:
            tags.append(x["name"])
            if t := x["translated_name"]:
                tags.append(t)
        tags = "; ".join([f"<code>{escape(x)}</code>" for x in tags])

        caption = (
            f"PixivSync - 收藏夹自动同步\n"
            f'From: <a href="https://www.pixiv.net/users/{api.user_id}">{escape(api.user_name or "")}</a>\n'
            f"{LINE_SEP}\n"
            f'PID: <code>{i["id"]}</code>\n'
            f'Title: <a href="https://www.pixiv.net/artworks/{i["id"]}">{escape(i["title"])}</a>\n'
            f'Artist: <a href="https://www.pixiv.net/users/{i["user"]["id"]}">{escape(i["user"]["name"])}</a>\n'
            f"Tags: {tags}"
        )

        urls: list[str] = []
        files: list[PluginCache] = []
        if i.get("meta_single_page"):
            urls.append(i["meta_single_page"]["original_image_url"])
        elif p := i.get("meta_pages"):
            urls.extend([x["image_urls"]["original"] for x in p])
        else:
            await bot.send_message(
                chat_id=_chat_id,
                text=f'WARN: 作品 <a href="https://www.pixiv.net/artworks/{i["id"]}">{escape(i["title"])}</a> 没有图片，跳过同步',
                parse_mode="HTML",
            )
            success += 1
            continue

        async def req(_u):
            async with ClientSession() as s:
                async with s.get(
                    _u,
                    proxy=config.telegram_proxy,
                    headers={
                        "Referer": "https://www.pixiv.net/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
                    },
                ) as r:
                    pic = await r.read()
            cache = PluginCache(_u.split("/")[-1])
            await cache.set_bytes(pic)
            files.append(cache)  # 防止对象销毁  # noqa: B023

        tasks = []
        for u in urls:
            tasks.append(req(u))

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.exception("下载图片失败")
            await bot.send_message(
                chat_id=_chat_id,
                text=(
                    f"ERROR: 同步作品 "
                    f'<a href="https://www.pixiv.net/artworks/{i["id"]}">'
                    f'{escape(i["title"])}</a> 时出错！\n'
                    f"下载图片失败\n"
                    f"{escape(repr(e))}"
                ),
                parse_mode="HTML",
            )
            fail += 1
            continue

        failed = False
        for chat_id in config.pixiv_sync_to_chats:
            try:
                if len(files) == 1:
                    await bot.send_document(
                        chat_id=chat_id,
                        document=files[0].get_path(),
                        caption=caption,
                        parse_mode="HTML",
                    )
                    await asyncio.sleep(config.pixiv_send_delay)  # QPS限制
                else:
                    docs = [InputMediaDocument(media=x.get_path()) for x in files]
                    docs.sort(
                        key=lambda it: int(it.media.split("_p")[-1].split(".")[0]),
                    )
                    docs[-1].caption = caption
                    docs[-1].parse_mode = "HTML"

                    g_id = None
                    d_len = len(docs)
                    for ii, d in enumerate(split_list(docs, 10)):
                        g_id = (
                            await bot.send_media_group(
                                chat_id=chat_id,
                                media=d,
                                reply_to_message_id=g_id,
                            )
                        )[-1].message_id
                        # 合并消息QPS限制更大（因为一张图等于一条消息）
                        await asyncio.sleep(
                            60
                            if (d_len > 1 and ii < (d_len - 1))
                            else config.pixiv_sync_delay,
                        )
            except Exception as e:
                logger.exception("上传图片失败")
                await bot.send_message(
                    chat_id=_chat_id,
                    text=(
                        f"ERROR: 同步作品 "
                        f'<a href="https://www.pixiv.net/artworks/{i["id"]}">'
                        f'{escape(i["title"])}</a> 时出错！\n'
                        f"上传图片失败\n"
                        f"{escape(repr(e))}"
                    ),
                    parse_mode="HTML",
                )
                failed = True
                fail += 1
                break

        if not failed:
            success += 1
            synced.append(i["id"])
            await data.set(str(api.user_id), synced)

    await edit_message_text(  # noqa: RET503
        f"同步完成！\n共计 {total}，成功 {success}，失败 {fail}\n如有失败项，建议重新执行指令同步一遍",
    )
