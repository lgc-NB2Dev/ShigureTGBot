from base64 import urlsafe_b64encode
from hashlib import sha256
from secrets import token_urlsafe
from urllib.parse import urlencode

from pixivpy_async.aapi import AppPixivAPI

LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"


class PixivAPI(AppPixivAPI):
    def __init__(self, **requests_kwargs):
        super().__init__(**requests_kwargs)
        self.user_name = None

        self.login_code_verifier = None

    async def login_web_part1(self):
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
        self.login_code_verifier = code_verifier

        return f"{LOGIN_URL}?{urlencode(login_params)}"

    async def login_web_part2(self, code):
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": self.login_code_verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"User-Agent": self.user_agent}

        ret = await self.auth_req(self.api.auth, headers, data)
        self.login_code_verifier = None
        self.user_name = ret["user"]["name"]

        return ret
