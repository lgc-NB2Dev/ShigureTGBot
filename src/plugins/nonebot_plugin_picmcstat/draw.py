import base64
import socket
from asyncio.exceptions import TimeoutError
from io import BytesIO
from typing import Optional, Union

from mcstatus import BedrockServer, JavaServer
from mcstatus.bedrock_status import BedrockStatusResponse
from mcstatus.pinger import PingResponse
from nonebot import get_driver
from nonebot.adapters.telegram.message import File, MessageSegment
from nonebot.log import logger
from PIL.Image import Resampling
from pil_utils import BuildImage, Text2Image

from .config import config
from .const import CODE_COLOR, GAME_MODE_MAP, STROKE_COLOR, ServerType
from .res import DEFAULT_ICON_RES, DIRT_RES, GRASS_RES
from .util import (
    format_code_to_bbcode,
    format_list,
    get_latency_color,
    json_to_format_code,
    strip_lines,
)

MARGIN = 32
MIN_WIDTH = 512
TITLE_FONT_SIZE = 8 * 5
EXTRA_FONT_SIZE = 8 * 4
EXTRA_STROKE_WIDTH = 2
STROKE_RATIO = 0.0625
EXTRA_SPACING = 12

JE_HEADER = "[MCJE服务器信息]"
BE_HEADER = "[MCBE服务器信息]"
SUCCESS_TITLE = "请求成功"


def get_header_by_svr_type(svr_type: ServerType) -> str:
    return JE_HEADER if svr_type == "je" else BE_HEADER


def draw_bg(width: int, height: int) -> BuildImage:
    size = DIRT_RES.width
    bg = BuildImage.new("RGBA", (width, height))

    for hi in range(0, height, size):
        for wi in range(0, width, size):
            bg.paste(DIRT_RES if hi else GRASS_RES, (wi, hi))

    return bg


def build_img(
    header1: str,
    header2: str,
    extra: Optional[Text2Image] = None,
    icon: Optional[BuildImage] = None,
) -> BytesIO:
    if not icon:
        icon = DEFAULT_ICON_RES

    header_text_color = CODE_COLOR["f"]
    header_stroke_color = STROKE_COLOR["f"]

    header_height = 128
    half_header_height = int(header_height / 2)

    bg_width = extra.width + MARGIN * 2 if extra else MIN_WIDTH
    bg_height = header_height + MARGIN * 2
    if bg_width < MIN_WIDTH:
        bg_width = MIN_WIDTH
    if extra:
        bg_height += extra.height + int(MARGIN / 2)
    bg = draw_bg(bg_width, bg_height)

    if icon.size != (header_height, header_height):
        icon = icon.resize_height(
            header_height,
            inside=False,
            resample=Resampling.NEAREST,
        )
    bg.paste(icon, (MARGIN, MARGIN), alpha=True)

    bg.draw_text(
        (
            header_height + MARGIN + MARGIN / 2,
            MARGIN - 4,
            bg_width - MARGIN,
            half_header_height + MARGIN + 4,
        ),
        header1,
        halign="left",
        fill=header_text_color,
        max_fontsize=TITLE_FONT_SIZE,
        fontname=config.mcstat_font,
        stroke_ratio=STROKE_RATIO,
        stroke_fill=header_stroke_color,
    )
    bg.draw_text(
        (
            header_height + MARGIN + MARGIN / 2,
            half_header_height + MARGIN - 4,
            bg_width - MARGIN,
            header_height + MARGIN + 4,
        ),
        header2,
        halign="left",
        fill=header_text_color,
        max_fontsize=TITLE_FONT_SIZE,
        fontname=config.mcstat_font,
        stroke_ratio=STROKE_RATIO,
        stroke_fill=header_stroke_color,
    )

    if extra:
        extra.draw_on_image(
            bg.image,
            (MARGIN, int(header_height + MARGIN + MARGIN / 2)),
        )

    return bg.convert("RGB").save("PNG")


def format_extra(extra: str) -> Text2Image:
    return Text2Image.from_bbcode_text(
        format_code_to_bbcode(extra),
        EXTRA_FONT_SIZE,
        fill=CODE_COLOR["f"],
        fontname=config.mcstat_font,
        stroke_ratio=STROKE_RATIO,
        stroke_fill=STROKE_COLOR["f"],
        spacing=EXTRA_SPACING,
    )


def draw_help(svr_type: ServerType) -> BytesIO:
    cmd_prefix_li = list(get_driver().config.command_start)
    prefix = cmd_prefix_li[0] if cmd_prefix_li else ""

    extra_txt = f"查询Java版服务器: {prefix}motd <服务器IP>\n查询基岩版服务器: {prefix}motdpe <服务器IP>"
    return build_img(get_header_by_svr_type(svr_type), "使用帮助", format_extra(extra_txt))


def draw_java(res: PingResponse) -> BytesIO:
    icon = None
    if res.favicon:
        icon = BuildImage.open(BytesIO(base64.b64decode(res.favicon.split(",")[-1])))

    players_online = res.players.online
    players_max = res.players.max
    online_percent = (
        "{:.2f}".format(players_online / players_max * 100) if players_max else "?.??"
    )
    motd = strip_lines(json_to_format_code(res.raw["description"]))

    player_li = ""
    if res.players.sample:
        sample = [x.name for x in res.players.sample]
        player_li = f"\n§7玩家列表: §f{format_list(sample)}"

    mod_client = ""
    mod_total = ""
    mod_list = ""
    if mod_info := res.raw.get("modinfo"):
        if tmp := mod_info.get("type"):
            mod_client = f"§7Mod端类型: §f{tmp}\n"

        if tmp := mod_info.get("modList"):
            mod_total = f"§7Mod总数: §f{len(tmp)}\n"
            mod_list = f"§7Mod列表: §f{format_list(tmp)}\n"

    extra_txt = (
        f"{motd}§r\n"
        f"§7服务端名: §f{res.version.name}\n"
        f"{mod_client}"
        f"§7协议版本: §f{res.version.protocol}\n"
        f"§7当前人数: §f{players_online}/{players_max} ({online_percent}%)\n"
        f"{mod_total}"
        f"§7测试延迟: §{get_latency_color(res.latency)}{res.latency:.2f}ms"
        f"{player_li}"
        f"{mod_list}"
    )
    return build_img(JE_HEADER, SUCCESS_TITLE, format_extra(extra_txt), icon)


def draw_bedrock(res: BedrockStatusResponse) -> BytesIO:
    map_name = f"§7存档名称: §f{res.map}§r\n" if res.map else ""
    game_mode = (
        f"§7游戏模式: §f{GAME_MODE_MAP.get(res.gamemode, res.gamemode)}\n"
        if res.gamemode
        else ""
    )
    online_percent = (
        "{:.2f}".format(int(res.players_online) / int(res.players_max) * 100)
        if res.players_max
        else "?.??"
    )
    motd = strip_lines(res.motd)

    extra_txt = (
        f"{motd}§r\n"
        f"§7协议版本: §f{res.version.protocol}\n"
        f"§7游戏版本: §f{res.version.version}\n"
        f"§7在线人数: §f{res.players_online}/{res.players_max} ({online_percent}%)\n"
        f"{map_name}"
        f"{game_mode}"
        f"§7测试延迟: §{get_latency_color(res.latency)}{res.latency:.2f}ms"
    )
    return build_img(BE_HEADER, SUCCESS_TITLE, format_extra(extra_txt))


def draw_error(e: Exception, svr_type: ServerType) -> BytesIO:
    extra = ""
    if isinstance(e, TimeoutError):
        reason = "请求超时"
    elif isinstance(e, socket.gaierror):
        reason = "域名解析失败"
        extra = str(e)
    else:
        reason = "出错了！"
        extra = repr(e)

    extra_img = format_extra(extra).wrap(MIN_WIDTH - MARGIN * 2) if extra else None

    return build_img(get_header_by_svr_type(svr_type), reason, extra_img)


async def draw(ip: str, svr_type: ServerType) -> Union[MessageSegment, str]:
    if svr_type not in ("je", "be"):
        raise ValueError("Server type must be `je` or `be`")  # noqa: TRY003

    try:
        if not ip:
            return File.photo(draw_help(svr_type).getvalue())

        if svr_type == "je":
            return File.photo(
                draw_java(
                    await (await JavaServer.async_lookup(ip)).async_status(),
                ).getvalue(),
            )

        return File.photo(
            draw_bedrock(await BedrockServer.lookup(ip).async_status()).getvalue(),
        )
    except Exception as e:
        logger.exception("获取服务器状态/画服务器状态图出错")
        try:
            return File.photo(draw_error(e, svr_type).getvalue())
        except:
            logger.exception("画异常状态图失败")
            return "出现未知错误，请检查后台输出"
