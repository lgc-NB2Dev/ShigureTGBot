import re
from dataclasses import dataclass


@dataclass
class LrcLine:
    time: int
    """Lyric Time (ms)"""
    lrc: str
    """Lyric Content"""


LRC_TIME_REGEX = r"(?P<min>\d+):(?P<sec>\d+)([\.:](?P<mili>\d+))?"
LRC_LINE_REGEX = re.compile(rf"^((\[{LRC_TIME_REGEX}\])+)(?P<lrc>.*)$", re.M)


def parse(lrc: str, ignore_empty: bool = True) -> list[LrcLine]:
    parsed = []
    for line in re.finditer(LRC_LINE_REGEX, lrc):
        lrc = line["lrc"].strip().replace("\u3000", " ")
        times = [x.groupdict() for x in re.finditer(LRC_TIME_REGEX, line[0])]

        parsed.extend(
            [
                LrcLine(
                    time=(
                        int(i["min"]) * 60 * 1000
                        + int(i["sec"]) * 1000
                        + int(i["mili"] or 0)
                    ),
                    lrc=lrc,
                )
                for i in times
            ],
        )

    if ignore_empty:
        parsed = [x for x in parsed if x.lrc]

    parsed.sort(key=lambda x: x.time)
    return parsed


def merge(*lrcs: list[LrcLine]) -> list[list[LrcLine]]:
    lrcs = tuple(x.copy() for x in lrcs)

    merged: list[list[LrcLine]] = []
    last_time = 0

    main_lrc = lrcs[0]
    sub_lrc = lrcs[1:]

    for line in main_lrc:
        will_merge = [line]
        last_time = line.time

        for sub in sub_lrc:
            index = None

            for i, lrc in enumerate(sub):
                if lrc.time == last_time:
                    index = i
                    break

            if index is not None:
                for _ in range(index + 1):
                    will_merge.append(sub.pop(0))

        merged.append(will_merge)

    for s in sub_lrc:
        merged[-1].extend(s)

    return merged
