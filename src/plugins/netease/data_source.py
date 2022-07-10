from nonebot import logger, get_driver
from pyncm import GetCurrentSession
from pyncm.apis import LoginFailedException
from pyncm.apis.cloudsearch import GetSearchResult, SONG
from pyncm.apis.login import LoginViaCellphone
from pyncm.apis.track import GetTrackDetail, GetTrackAudio

from .async_wrapper import wrapper
from .config import config

driver = get_driver()
GetCurrentSession().headers["X-Real-IP"] = "118.88.88.88"


async def login():
    phone = config.netease_phone
    pwd = config.netease_pwd

    logger.info("开始登录网易云音乐")
    try:
        ret = await wrapper(LoginViaCellphone, phone=phone, password=pwd)
        nick = ret["content"]["profile"]["nickname"]
    except LoginFailedException as e:
        logger.opt(exception=e).exception("登录失败，功能将会受到限制")
        # raise e
        return
    logger.info(f"欢迎您，{nick}")


async def search(name, limit=config.netease_list_limit, page=1, stype=SONG):
    offset = limit * (page - 1)
    return await wrapper(GetSearchResult, name, stype=stype, limit=limit, offset=offset)


async def get_track_info(ids: list):
    return await wrapper(GetTrackDetail, ids)


async def get_track_audio(song_ids: list, bit_rate=320000, encode_type="aac"):
    return await wrapper(
        GetTrackAudio, song_ids, bitrate=bit_rate, encodeType=encode_type
    )
