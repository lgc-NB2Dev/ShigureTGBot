from nonebot import on_command
from nonebot.matcher import Matcher


@on_command('start').handle()
def _(matcher: Matcher):
    await matcher.send('你好~我是Shigure~\n'
                       '目前Bot功能正在持续开发中，不妨看看命令菜单都有些啥吧！')
