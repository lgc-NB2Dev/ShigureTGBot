"""
pixiv收藏夹自动同步

.env配置
PIXIV_OAUTH_USER 使用oauth登录时登录链接发送到的chat id
PIXIV_SYNC_TO_CHATS 要将你收藏夹同步到的chat id
PIXIV_SYNC_DELAY 收藏夹同步间隔（秒）
"""
from .__main__ import *

__version__ = "0.1.0"
