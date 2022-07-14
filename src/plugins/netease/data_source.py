from nonebot import logger
from pyncm import GetCurrentSession
from pyncm.apis import LoginFailedException
from pyncm.apis.cloudsearch import GetSearchResult, SONG
from pyncm.apis.login import LoginViaCellphone
from pyncm.apis.track import GetTrackDetail, GetTrackAudio

from .config import config
from ..base.util import async_wrapper as wrapper

if config.netease_fake_ip:
    GetCurrentSession().headers["X-Real-IP"] = config.netease_fake_ip


async def login():
    if config.netease_login:
        logger.info("开始登录网易云音乐")
        try:
            ret = await wrapper(
                LoginViaCellphone,
                phone=config.netease_phone,
                password=config.netease_pwd,
                ctcode=config.netease_ct_code,
            )
            nick = ret["content"]["profile"]["nickname"]
        except LoginFailedException as e:
            logger.opt(exception=e).exception("登录失败，功能将会受到限制")
            return e
        logger.info(f"欢迎您，{nick}")


async def search(name, limit=config.netease_list_limit, page=1, stype=SONG):
    offset = limit * (page - 1)
    res = await wrapper(GetSearchResult, name, stype=stype, limit=limit, offset=offset)
    logger.debug(f"GetSearchResult - {res}")
    return res


async def get_track_info(ids: list):
    res = await wrapper(GetTrackDetail, ids)
    logger.debug(f"GetTrackDetail - {res}")
    return res


async def get_track_audio(song_ids: list, bit_rate=320000, encode_type="aac"):
    res = await wrapper(
        GetTrackAudio, song_ids, bitrate=bit_rate, encodeType=encode_type
    )
    logger.debug(f"GetTrackAudio - {res}")
    return res
