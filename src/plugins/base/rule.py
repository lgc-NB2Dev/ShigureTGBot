from nonebot.adapters.telegram.event import CallbackQueryEvent
from nonebot.typing import T_State


def inline_rule(prefix):
    def r(event: CallbackQueryEvent, state: T_State):
        data = event.data.split("|")
        state["data"] = data
        if data[0] == prefix:
            return True

    return r
