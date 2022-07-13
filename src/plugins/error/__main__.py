import time
import traceback

from aiohttp import ClientSession, FormData
from nonebot import get_driver, get_bot, logger
from nonebot.adapters.telegram import Bot
from nonebot.message import run_postprocessor

driver = get_driver()


@run_postprocessor
async def _(e: Exception):
    name = f'Shigure_Error_{time.strftime("%Y-%m-%d_%H-%M-%S")}'
    stack = "".join(traceback.format_exception(type(e), e, e.__traceback__))

    async with ClientSession() as s:
        data = FormData()
        data.add_field("author", "ShigureTGBot")
        data.add_field("encrypt_algorithm", "")
        data.add_field("file", stack.encode(), filename=name)
        async with s.post("https://paste.shoujo.io/api/v0/upload", data=data) as r:
            note_id = (await r.text()).strip('"')
            note_url = f"https://paste.shoujo.io/{note_id}"

    bot: Bot = get_bot()
    text = f"呜呜……Shigure遇到了错误！\n" f'<a href="{note_url}">点击这里查看错误堆栈</a>'
    for s in driver.config.superusers:
        try:
            await bot.send_message(chat_id=int(s), text=text, parse_mode="HTML")
        except:
            logger.exception(f"向SuperUser {s} 发送报错堆栈链接失败")


"""
@on_command('testbugreport', '测试Bug上报').handle()
async def _():
    raise Exception('Test')
"""
