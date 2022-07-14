import asyncio
import random
import re

from aiohttp import ClientSession
from nonebot import get_driver, get_bot, logger
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot_plugin_apscheduler import scheduler

from .config import config, data, global_config
from .data_source import api, login
from ..base.cmd import on_command
from ..base.const import LINE_SEP

driver = get_driver()
bot_connected = False


@driver.on_bot_connect
async def _(bot: Bot):
    global bot_connected

    if not bot_connected:
        bot_connected = True
        await login(bot)


@on_command("pixiv_relogin", "Pixiv重登", hide=True, permission=SUPERUSER).handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent):
    await matcher.send("重新登录中……", reply_to_message_id=event.message_id)
    await login(bot)


@scheduler.scheduled_job("interval", seconds=config.pixiv_sync_delay)
async def _():
    logger.info("开始同步收藏夹")
    synced = data.get(str(api.user_id), [])
    will_sync = []

    def add_will_sync(illusts_):
        for it in illusts_:
            if it["id"] in synced:
                return True
            will_sync.append(it)

    max_bookmark_id = None
    while True:
        logger.info("获取一页收藏……")
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
        max_bookmark_id = max_bookmark_id.group(1)
        # print(max_bookmark_id)

    synced.extend([x["id"] for x in will_sync])
    await data.set(str(api.user_id), synced)

    logger.info(f"已取得所有未同步收藏（共{len(will_sync)}个），发送中")
    bot: Bot = get_bot()
    will_sync.reverse()
    for i in will_sync:
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
                        i["image_urls"]["medium"],  # tg会压缩图片，还不如发压缩图
                        proxy=global_config.telegram_proxy,
                        headers={
                            "Referer": "https://www.pixiv.net/",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
                        },
                    ) as r:
                        pic = await r.read()
                await bot.send_photo(
                    chat_id=chat_id, photo=pic, caption=caption, parse_mode="HTML"
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
    logger.info("同步结束")
