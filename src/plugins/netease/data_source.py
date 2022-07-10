from nonebot import logger, get_driver
from pyncm import GetCurrentSession
from pyncm.apis import LoginFailedException
from pyncm.apis.cloudsearch import GetSearchResult, SONG
from pyncm.apis.login import LoginViaCellphone
from pyncm.apis.track import GetTrackDetail, GetTrackAudio

from .async_wrapper import wrapper

driver = get_driver()
GetCurrentSession().headers['X-Real-IP'] = '118.88.88.88'

async def login():
    phone = getattr(driver.config, "netease_phone")
    pwd = getattr(driver.config, "netease_pwd")

    if (not phone) or (not pwd):
        raise ValueError("请在env文件配置 NETEASE_PHONE 与 NETEASE_PWD")

    logger.info("开始登录网易云音乐")
    try:
        ret = await wrapper(LoginViaCellphone, phone=phone, password=pwd)
        nick = ret["content"]["profile"]["nickname"]
    except LoginFailedException as e:
        logger.error("登录失败")
        raise e
    logger.info(f"欢迎您，{nick}")


async def search(name, limit=9, page=1, stype=SONG):
    offset = limit * (page - 1)
    return await wrapper(
        GetSearchResult, name, stype=stype, limit=limit, offset=offset
    )


async def get_track_info(ids: list):
    return await wrapper(GetTrackDetail, ids)


async def get_track_audio(song_ids: list, bit_rate=320000, encode_type="aac"):
    return await wrapper(
        GetTrackAudio, song_ids, bitrate=bit_rate, encodeType=encode_type
    )
