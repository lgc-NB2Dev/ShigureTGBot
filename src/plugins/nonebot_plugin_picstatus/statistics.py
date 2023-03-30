from datetime import datetime
from typing import Dict, Optional

from nonebot import get_driver, on_message
from nonebot.internal.adapter import Bot

# bot_connect_time: Dict[str, datetime] = {}
nonebot_run_time = datetime.now()
recv_num: Dict[str, int] = {}
send_num: Dict[str, int] = {}

driver = get_driver()


async def called_api(bot: Bot, exc: Optional[Exception], api: str, _, __):
    if (not exc) and api.startswith("send"):
        num = send_num.get(bot.self_id, 0)
        send_num[bot.self_id] = num + 1


@driver.on_bot_connect
def _(bot: Bot):
    # bot_connect_time[bot.self_id] = datetime.now()
    bot.on_called_api(called_api)


mat_rec = on_message(block=False)


@mat_rec.handle()
async def _(bot: Bot):
    num = recv_num.get(bot.self_id, 0)
    recv_num[bot.self_id] = num + 1
