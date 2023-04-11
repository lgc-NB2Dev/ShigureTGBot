from typing import Any, Optional

from nonebot import logger
from nonebot.adapters.telegram import Bot
from pyncm import (
    DumpSessionAsString,
    GetCurrentSession,
    LoadSessionFromString,
    SetCurrentSession,
)
from pyncm.apis.cloudsearch import SONG, GetSearchResult
from pyncm.apis.login import LoginViaCellphone
from pyncm.apis.track import GetTrackAudio, GetTrackDetail, GetTrackLyrics

from ..base.util import async_wrapper as wrapper
from .config import config, session

if isinstance(config.netease_fake_ip, str):
    GetCurrentSession().headers["X-Real-IP"] = config.netease_fake_ip


# async def check_in(bot_arg: Optional[Bot] = None, chat_id: Optional[int] = None):
#     bot = bot_arg or cast(Bot, get_bot())
#     if not chat_id:
#         chat_id = config.superusers[0]

#     logger.info("尝试签到")
#     ret = cast(dict[str, Any], await wrapper(SetSignin, SIGNIN_TYPE_MOBILE))
#     logger.info(f"签到完毕，请根据返回值检查 Session 状态\n{ret}")
#     await bot.send_message(
#         chat_id=chat_id,
#         text=f"尝试在网易云音乐网页端签到，请根据返回值检查 Session 状态\n{ret}",
#     )


async def login(_: Optional[Bot] = None, __: Optional[int] = None):
    if not config.netease_login:
        return ValueError("配置文件中 netease_login 不为真")

    if session_str := session.get("session"):
        logger.info("尝试恢复网易云音乐会话")
        try:
            SetCurrentSession(LoadSessionFromString(session_str))
            # await check_in(bot, chat_id)
            logger.info(f"欢迎您，{GetCurrentSession().nickname}")
        except:
            logger.exception("恢复会话失败，使用正常流程登录")
            await session.delete("session")
        else:
            return None

    logger.info("开始登录网易云音乐")
    try:
        ret = await wrapper(
            LoginViaCellphone,
            phone=config.netease_phone,  # type: ignore  # noqa: PGH003
            password=config.netease_pwd,  # type: ignore  # noqa: PGH003
            ctcode=config.netease_ct_code,
        )
        # await check_in(bot, chat_id)
        nick = ret["result"]["content"]["profile"]["nickname"]
    except Exception as e:
        logger.opt(exception=e).exception("登录失败，功能将会受到限制")
        return e

    session_str = DumpSessionAsString(GetCurrentSession())
    await session.set("session", session_str)

    logger.info(f"欢迎您，{nick}")
    return None


async def search(
    name,
    limit=config.netease_list_limit,
    page=1,
    stype=SONG,
) -> dict[str, Any]:
    offset = limit * (page - 1)
    res = await wrapper(GetSearchResult, name, stype=stype, limit=limit, offset=offset)
    logger.debug(f"GetSearchResult - {res}")
    return res  # type: ignore  # noqa: PGH003


async def get_track_info(ids: list) -> dict[str, Any]:
    res = await wrapper(GetTrackDetail, ids)
    logger.debug(f"GetTrackDetail - {res}")
    return res  # type: ignore  # noqa: PGH003


async def get_track_audio(
    song_ids: list,
    bit_rate=320000,
    encode_type="aac",
) -> dict[str, Any]:
    res = await wrapper(
        GetTrackAudio,
        song_ids,
        bitrate=bit_rate,
        encodeType=encode_type,
    )
    logger.debug(f"GetTrackAudio - {res}")
    return res  # type: ignore  # noqa: PGH003


async def get_track_lrc(song_id: str) -> dict[str, Any]:
    res = await wrapper(GetTrackLyrics, song_id)
    logger.debug(f"GetTrackLyrics - {res}")
    return res  # type: ignore  # noqa: PGH003
