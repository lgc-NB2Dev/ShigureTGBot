import json
import random
import re
from contextlib import suppress
from typing import TYPE_CHECKING, List, Optional, Union

from .const import (
    CODE_COLOR,
    FORMAT_CODE_REGEX,
    STRING_CODE,
    STROKE_COLOR,
    STYLE_BBCODE,
)

if TYPE_CHECKING:
    from mcstatus.pinger import RawResponseDescription, RawResponseDescriptionWhenDict


RANDOM_CHAR_TEMPLATE = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!§$%&?#"
)


def get_latency_color(delay: Union[int, float]) -> str:
    if delay <= 50:
        return "a"
    if delay <= 100:
        return "e"
    if delay <= 200:
        return "6"
    return "c"


def random_char(length: int) -> str:
    return "".join(random.choices(RANDOM_CHAR_TEMPLATE, k=length))


def strip_lines(txt: str) -> str:
    head_space_regex = re.compile(rf"^(({FORMAT_CODE_REGEX})+)\s+", re.M)
    tail_space_regex = re.compile(rf"\s+(({FORMAT_CODE_REGEX})+)$", re.M)

    txt = "\n".join([x.strip() for x in txt.splitlines()])
    txt = re.sub(head_space_regex, r"\1", txt)
    txt = re.sub(tail_space_regex, r"\1", txt)
    return txt


def replace_format_code(txt: str, new_str: str = "") -> str:
    return re.sub(FORMAT_CODE_REGEX, new_str, txt)


def format_code_to_bbcode(text: str) -> str:
    if not text:
        return text

    parts = text.split("§")
    parsed: List[str] = [parts[0]]
    color_tails: List[str] = []
    format_tails: List[str] = []

    for p in parts[1:]:
        char = p[0]
        txt = p[1:]

        if char in CODE_COLOR:
            parsed.extend(color_tails)
            color_tails.clear()
            parsed.append(f"[stroke={STROKE_COLOR[char]}][color={CODE_COLOR[char]}]")
            color_tails.append("[/color][/stroke]")

        elif char in STYLE_BBCODE:
            head, tail = STYLE_BBCODE[char]
            format_tails.append(tail)
            parsed.append(head)

        elif char == "r":  # reset
            parsed.extend(color_tails)
            parsed.extend(format_tails)

        elif char == "k":  # random
            txt = random_char(len(txt))

        else:
            txt = f"§{char}{txt}"

        parsed.append(txt)

    parsed.extend(color_tails)
    parsed.extend(format_tails)
    return "".join(parsed)


def format_list(
    sample: List[str],
    items_per_line=2,
    line_start_spaces=10,
    list_gap=2,
) -> str:
    sample = [x for x in sample if x]
    if not sample:
        return ""

    max_width = max([len(replace_format_code(x)) for x in sample]) + list_gap

    line_added = 0
    tmp = []
    for name in sample:
        if line_added < items_per_line:
            code_len = len(name) - len(replace_format_code(name))
            name = name.ljust(max_width + code_len)

        tmp.append(name)
        line_added += 1

        if line_added >= items_per_line:
            tmp.append("\n")
            tmp.append(" " * line_start_spaces)
            line_added = 0

    return "".join(tmp).strip()


def get_format_code_by_dict(json: "RawResponseDescriptionWhenDict") -> list:
    codes = []
    if color := json.get("color"):
        codes.append(f"§{STRING_CODE[color]}")

    for k in ["bold", "italic", "underlined", "strikethrough", "obfuscated"]:
        if json.get(k):
            codes.append(f"§{STRING_CODE[k]}")
    return codes


def json_to_format_code(
    raw_json: "RawResponseDescription",
    interpret: Optional[bool] = None,
) -> str:
    if isinstance(raw_json, str):
        return raw_json
    if isinstance(raw_json, list):
        return "§r".join([json_to_format_code(x, interpret) for x in raw_json])

    interpret = interpret if (i := raw_json.get("interpret")) is None else i
    code = "".join(get_format_code_by_dict(raw_json))
    texts = []

    if text := raw_json.get("text"):
        if interpret:
            with suppress(Exception):
                text = json_to_format_code(json.loads(text), interpret)
        texts.append(text)

    if extra := raw_json.get("extra"):
        texts.append(json_to_format_code(extra, interpret))

    return f"{code}{''.join(texts)}"
