from nonebot.adapters.telegram.event import MessageEvent
from nonebot.matcher import Matcher

from ..base.cmd import on_command
from ..base.const import LINE_SEP


@on_command("about", "关于Bot").handle()
async def _(matcher: Matcher, event: MessageEvent):
    await matcher.send(
        (
            "关于Shigure\n"
            f"{LINE_SEP}\n"
            '开发者：<a href="https://t.me/lgc2333">@lgc2333</a>\n'
            '开源地址：<a href="https://github.com/lgc2333/ShigureTGBot">Github</a>\n'
            '使用框架：<a href="https://github.com/nonebot/nonebot2">NoneBot2</a>\n'
            "鸣谢：\n"
            '  - <a href="https://github.com/MinatoAquaCrews/nonebot_plugin_crazy_thursday">'
            "nonebot-plugin-crazy-thursday</a>\n"
            "    疯狂星期四语录原插件\n"
            '  - <a href="https://github.com/xipesoy/zhenxun_plugin_meiriyiju">'
            "zhenxun-plugin-meiriyiju</a>\n"
            "    发癫语录原插件\n"
            f"{LINE_SEP}\n"
            '<a href="https://t.me/stu2333_pd/50">请我喝杯奶茶</a> | '
            '<a href="https://t.me/stu2333_home">一起聊天</a>'
        ),
        reply_to_message_id=event.message_id,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
