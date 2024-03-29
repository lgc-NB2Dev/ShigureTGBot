import json
import os
import platform
import re
from datetime import timedelta
from io import BytesIO
from typing import Literal, Optional, cast, overload

import aiofiles
from httpx import AsyncClient
from nonebot import logger
from nonebot.adapters.telegram import Bot
from PIL import Image

from .config import config


def format_timedelta(t: timedelta):
    mm, ss = divmod(t.seconds, 60)
    hh, mm = divmod(mm, 60)
    s = "%d:%02d:%02d" % (hh, mm, ss)
    if t.days:
        s = ("%d天 " % t.days) + s
    # if t.microseconds:
    #     s += " %.3f 毫秒" % (t.microseconds / 1000)
    return s


@overload
async def async_request(
    url: str,
    *args,
    is_text: Literal[False] = False,
    proxy: Optional[str] = None,
    **kwargs,
) -> bytes:
    ...


@overload
async def async_request(
    url: str,
    *args,
    is_text: Literal[True] = True,
    proxy: Optional[str] = None,
    **kwargs,
) -> str:
    ...


async def async_request(url: str, *args, is_text=False, proxy=None, **kwargs):
    async with AsyncClient(proxies=proxy) as cli:
        res = await cli.get(url, *args, **kwargs)
        return res.text if is_text else res.content


async def get_anime_pic():
    r: str = json.loads(
        await async_request(
            "https://api.lolicon.app/setu/v2",
            is_text=True,
            proxy=config.proxy,
            params={"proxy": 0, "excludeAI": 1, "tag": "萝莉|少女"},
        ),
    )
    return await async_request(
        r["data"][0]["urls"]["original"],  # type: ignore  # noqa: PGH003
        proxy=config.proxy,
        headers={"referer": "https://pixiv.net/"},
    )


async def download_file(bot: Bot, file_id: str) -> bytes:
    res = await bot.get_file(file_id=file_id)
    file_path = cast(str, res.file_path)

    if os.path.exists(file_path):  # noqa: PTH110
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    url = f"{bot.bot_config.api_server}file/bot{bot.bot_config.token}/{file_path}"
    return await async_request(url, proxy=config.proxy)


async def get_tg_avatar(bot: Bot):
    res = await bot.get_user_profile_photos(user_id=int(bot.self_id), limit=1)
    file_id = res.photos[0][-1].file_id

    return await download_file(bot, file_id)


async def async_open_img(fp, *args, **kwargs) -> Image.Image:
    async with aiofiles.open(fp, "rb") as f:
        p = BytesIO(await f.read())
    return Image.open(p, *args, **kwargs)


async def get_system_name():
    system, _, release, version, machine, _ = platform.uname()
    system, release, version = platform.system_alias(system, release, version)

    if system == "Java":
        _, _, _, (system, release, machine) = platform.java_ver()

    if system == "Darwin":
        return f"MacOS {platform.mac_ver()[0]} {machine}"
    if system == "Windows":
        return f"Windows {release} {platform.win32_edition()} {machine}"
    if system == "Linux":
        try:
            async with aiofiles.open("/etc/issue") as f:
                v: str = await f.read()
        except:
            logger.exception("读取 /etc/issue 文件失败")
            v = f"未知Linux {release}"
        else:
            v = v.replace(r"\n", "").replace(r"\l", "").strip()
        return f"{v} {machine}"

    return f"{system} {release}"


def format_byte_count(b: int):
    if (k := b / 1024) < 1:
        return f"{b}B"
    if (m := k / 1024) < 1:
        return f"{k:.2f}K"
    if (g := m / 1024) < 1:
        return f"{m:.2f}M"
    return f"{g:.2f}G"


def match_list_regexp(reg_list, txt):
    for r in reg_list:
        if m := re.search(r, txt):
            return m
    return None
