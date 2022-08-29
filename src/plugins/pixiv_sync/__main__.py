import asyncio
import random
import re

from aiohttp import ClientSession
from nonebot import get_driver, get_bot, logger
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import EventPlainText
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

from .config import config, data
from .data_source import PixivAPI
from ..base.cmd import on_command
from ..base.const import LINE_SEP
from ..cache import PluginCache

driver = get_driver()
bot_connected = False

handler = on_command("pixiv_sync", "Pixiv收藏夹同步", hide=True, permission=SUPERUSER)


@handler.handle()
async def _1(matcher: Matcher, event: MessageEvent, state: T_State):
    state["api"] = (api := PixivAPI(proxy=config.telegram_proxy))
    state["old_msg_id"] = (
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
        )
    )["result"]["message_id"]
    await matcher.pause()


@handler.handle()
async def _2(
    bot: Bot,
    matcher: Matcher,
    state: T_State,
    event: MessageEvent,
    code: str = EventPlainText(),
):
    api = state["api"]
    msg_id = (await matcher.send("登录中"))["result"]["message_id"]
    await bot.delete_message(chat_id=event.chat.id, message_id=state["old_msg_id"])

    try:
        await api.login_web_part2(code.strip())
    except Exception as e:
        logger.opt(exception=e).exception("登录失败")
        await bot.edit_message_text(
            text=f"登录失败\n{e!r}", chat_id=event.chat.id, message_id=msg_id
        )
        return await matcher.finish()

    await bot.edit_message_text(
        text=f"登录成功\n欢迎，{api.user_name}", chat_id=event.chat.id, message_id=msg_id
    )

    try:
        await sync(bot, event, api, msg_id)
    except Exception as e:
        logger.opt(exception=e).exception("同步失败")
        await matcher.send(message=f"同步失败\n{e!r}", reply_to_message_id=msg_id)


async def sync(bot: Bot, event: MessageEvent, api: PixivAPI, reply_id):
    msg_id = (await bot.send(event, "同步中……", reply_to_message_id=reply_id))["result"][
        "message_id"
    ]

    async def edit_message_text(text_):
        await bot.edit_message_text(
            text=text_, chat_id=event.chat.id, message_id=msg_id
        )

    synced = data.get(str(api.user_id), [])
    will_sync = []

    def add_will_sync(illusts_):
        for it in illusts_:
            # print(it)
            if it["id"] in synced:
                return True
            will_sync.append(it)

    max_bookmark_id = None
    i = 1
    while True:
        await edit_message_text(f"获取第 {i} 页收藏")
        bookmarks = await api.user_bookmarks_illust(
            api.user_id, max_bookmark_id=max_bookmark_id
        )
        illusts = bookmarks["illusts"]
        if add_will_sync(illusts):
            break

        await asyncio.sleep(random.randint(1, 3))
        if not (
            (next_url := bookmarks["next_url"])
            and (max_bookmark_id := re.search("max_bookmark_id=([0-9]+)", next_url))
        ):
            break
        max_bookmark_id = max_bookmark_id[1]
        # print(max_bookmark_id)
        i += 1

    bot: Bot = get_bot()
    will_sync.reverse()

    total = len(will_sync)
    if total == 0:
        return await edit_message_text("没有收藏可以同步")

    success = 0
    fail = 0
    for n, i in enumerate(will_sync):

        def get_tip():
            return f"正在发送 {n + 1} / {total}\n成功 {success}，失败 {fail}"

        await edit_message_text(get_tip())

        caption = (
            f"PixivSync - 收藏夹自动同步\n"
            f'From: <a href="https://www.pixiv.net/users/{api.user_id}">{api.user_name}</a>\n'
            f"{LINE_SEP}\n"
            f'PID: {i["id"]}\n'
            f'Title: <a href="https://www.pixiv.net/artworks/{i["id"]}">{i["title"]}</a>\n'
            f'Artist: <a href="https://www.pixiv.net/users/{i["user"]["id"]}">{i["user"]["name"]}</a>'
        )
        for chat_id in config.pixiv_sync_to_chats:
            try:
                async with ClientSession() as s:
                    async with s.get(
                        i["meta_single_page"]["original_image_url"],
                        proxy=config.telegram_proxy,
                        headers={
                            "Referer": "https://www.pixiv.net/",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
                        },
                    ) as r:
                        pic = await r.read()
                cache = PluginCache(f'{i["id"]}_original.png')
                await cache.set_bytes(pic)
                await bot.send_document(
                    chat_id=chat_id,
                    document=cache.get_path(),
                    caption=caption,
                    parse_mode="HTML",
                )
            except:
                logger.exception("上传图片失败")
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"<b>图片上传失败</b>\n{LINE_SEP}\n{caption}",
                        parse_mode="HTML",
                    )
                except:
                    logger.exception("消息发送失败")
                    fail += 1

                    data.data[str(api.user_id)].remove(i["id"])
                    await data.save()

                    continue

            success += 1
            await edit_message_text(get_tip())

            synced.append(i["id"])
            await data.set(str(api.user_id), synced)

            await asyncio.sleep(config.pixiv_send_delay)  # QPS限制

    await edit_message_text(
        f"同步完成！\n" f"共计 {total}，成功 {success}，失败 {fail}\n" f"如有失败项，建议重新执行指令同步一遍"
    )
