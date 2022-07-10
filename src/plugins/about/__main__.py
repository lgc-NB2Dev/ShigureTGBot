from nonebot.adapters.telegram.event import MessageEvent
from nonebot.matcher import Matcher

from ..base.cmd import on_command


@on_command('about', '关于Bot').handle()
async def _(matcher: Matcher, event: MessageEvent):
    await matcher.send(('关于Shigure\n'
                        '-=-=-=-=-=-=-=-=-=-\n'
                        '开发者：[@lgc2333](https://t.me/@lgc2333)\n'
                        '开源地址：[Github](https://github.com/lgc2333/ShigureTGBot)'
                        '使用框架：[Nonebot2](https://github.com/nonebot/nonebot2)\n'
                        '特别感谢：\n'
                        '  - [Wutzu](https://berthua.top/)（服务器提供）\n'
                        '-=-=-=-=-=-=-=-=-=-\n'
                        '[请我喝杯奶茶](https://t.me/stu2333_pd/50) | [一起聊天](https://t.me/stu2333_home)'
                        ).replace('-', '\-'),
                       reply_to_message_id=event.message_id,
                       parse_mode='MarkdownV2')
