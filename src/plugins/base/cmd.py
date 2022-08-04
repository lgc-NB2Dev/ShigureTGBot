"""
插件使用本插件注册命令，本插件自动将命令设置到Bot菜单
"""
from nonebot import get_driver, logger
from nonebot import on_command as raw_on_command
from nonebot.adapters.telegram import Bot, Message
from nonebot.adapters.telegram.event import MessageEvent, GroupMessageEvent
from nonebot.adapters.telegram.model import BotCommand as RawBotCommand
from nonebot.consts import PREFIX_KEY, CMD_ARG_KEY
from nonebot.internal.params import Depends
from nonebot.matcher import Matcher
from nonebot.params import RawCommand, CommandArg
from nonebot.typing import T_State

from ..base.const import LINE_SEP, CMD_TRUE_ARG_KEY

driver = get_driver()

command_list = []
bot_username = []


class BotCommand(RawBotCommand):
    hide: bool = False


async def command_rule(
        event: MessageEvent,
        state: T_State,
        arg: Message = CommandArg(),
        cmd: str = RawCommand(),
):
    def simple_check(msg_, cmd_):
        return msg_ == cmd_ or msg_.startswith(f"{cmd_} ")

    msg = event.message.extract_plain_text().strip()
    if simple_check(msg, cmd):
        return True
    if isinstance(event, GroupMessageEvent):
        for u in bot_username:
            group_cmd = f"{cmd}@{u}"
            if simple_check(msg, group_cmd):
                arg_copy = arg.copy()
                for i, m in enumerate(arg):
                    if m.data["text"] == f"@{u}":
                        arg_copy.pop(i)

                        arg_len = len(arg_copy)
                        if arg_len > 0:
                            t = arg_copy[i].data["text"]
                            arg_copy[i].data["text"] = t.lstrip()
                state[PREFIX_KEY][CMD_TRUE_ARG_KEY] = arg_copy
                return True


def on_command(cmd: str | tuple, desc: str, *args, hide=False, **kwargs):
    command_list.append(BotCommand(command=cmd, description=desc, hide=hide))

    if rule := kwargs.get("rule"):
        rule = rule & command_rule
        kwargs.pop("rule")
    else:
        rule = command_rule
    return raw_on_command(cmd, rule=rule, *args, **kwargs)


def CommandArg():
    """消息命令参数"""

    def _command_arg(state: T_State) -> Message:
        if (true_arg := state[PREFIX_KEY].get(CMD_TRUE_ARG_KEY)) is not None:
            return true_arg
        return state[PREFIX_KEY][CMD_ARG_KEY]

    return Depends(_command_arg)


def get_cmd_list_txt(show_hide=False):
    prefix = list(driver.config.command_start)[0]
    return "\n".join(
        [
            f"{prefix}{x.command} - {x.description}{'（隐藏）' if x.hide else ''}"
            for x in command_list
            if (not x.hide) or show_hide
        ]
    )


@driver.on_bot_connect
async def _(bot: Bot):
    command_list.sort(key=lambda x: x.command)

    bot_username.append(u := ((await bot.get_me())["result"]["username"]))
    logger.info(f"Bot {bot.self_id}(@{u}) connected")

    logger.info(f"Registered Commands:\n{get_cmd_list_txt(True)}")
    await bot.set_my_commands(commands=[x for x in command_list if not x.hide])


@on_command("menu", "功能列表").handle()
async def _(matcher: Matcher, event: MessageEvent):
    await matcher.send(
        "Shigure☆功能列表\n" f"{LINE_SEP}\n" f"{get_cmd_list_txt()}",
        reply_to_message_id=event.message_id,
    )
