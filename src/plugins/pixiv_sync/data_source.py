import asyncio

from nonebot import on_message, logger
from nonebot.adapters.telegram import Bot
from nonebot.adapters.telegram.event import MessageEvent
from pixivpy_async.aapi import AppPixivAPI

from .config import config, global_config


class PixivAPI(AppPixivAPI):
    def __init__(self, **requests_kwargs):
        super().__init__(**requests_kwargs)
        self.login_code = None
        self.user_name = None

    async def set_login_code(self, event: MessageEvent):
        self.login_code = event.get_plaintext()

    async def login_web_with_bot(self, bot):
        from base64 import urlsafe_b64encode
        from hashlib import sha256
        from secrets import token_urlsafe
        from urllib.parse import urlencode

        LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
        REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"

        def s256(data_):
            """S256 transformation method."""
            return (
                urlsafe_b64encode(sha256(data_).digest()).rstrip(b"=").decode("ascii")
            )

        """Proof Key for Code Exchange by OAuth Public Clients (RFC7636)."""
        code_verifier = token_urlsafe(32)
        code_challenge = s256(code_verifier.encode("ascii"))
        login_params = {
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "client": "pixiv-android",
        }

        await bot.send_message(
            chat_id=config.pixiv_oauth_user,
            text=(
                "[PixivSync]\n"
                f'<a href="{LOGIN_URL}?{urlencode(login_params)}">登录链接</a>\n'
                "请直接将Auth Token发给我\n"
                f'<a href="https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362">教程</a>'
            ),
            parse_mode="HTML",
        )

        async def rule(event: MessageEvent):
            return event.chat.id == config.pixiv_oauth_user

        on_message(temp=True, rule=rule).append_handler(self.set_login_code)

        while not self.login_code:
            await asyncio.sleep(0)
        code = self.login_code

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"User-Agent": self.user_agent}

        # return auth/token response
        return await self.auth_req(self.api.auth, headers, data)


async def login(bot: Bot):
    if config.pixiv_oauth_user:
        try:
            ret = await api.login_web_with_bot(bot)
        except Exception as e:
            logger.opt(exception=e).exception("Pixiv登录失败")
            return await bot.send_message(
                chat_id=config.pixiv_oauth_user, text=f"登录失败\n{e!r}"
            )
        user_name = ret["user"]["name"]
        await bot.send_message(
            chat_id=config.pixiv_oauth_user, text=f"登录成功，欢迎你，{user_name}"
        )
        api.user_name = user_name
    else:
        logger.info("Pixiv未登录")


api = PixivAPI(proxy=config.telegram_proxy)
