from nonebot.adapters.telegram.event import CallbackQueryEvent
from nonebot.typing import T_State


def inline_rule(prefix: str):
    async def r(event: CallbackQueryEvent, state: T_State):
        if not event.data:
            return False

        data = event.data.split("|")
        state["data"] = data

        return bool(data and data[0] == prefix)

    return r
