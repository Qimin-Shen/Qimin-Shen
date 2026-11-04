#!/usr/bin/env python3
"""Update the single daily check-in block in the profile README."""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

START = "<!-- daily-fortune-start -->"
END = "<!-- daily-fortune-end -->"
QUOTES = [
    "🌒 月影揺れ、言葉は風に消ゆ。",
    "🌓 静夜に、星の声が胸を打つ。",
    "🌕 雲を割り、白き月、ただ独り。",
    "🌘 鳥も眠る、夜の底に夢ひとつ。",
    "🌑 闇を抱き、光はなお生まれくる。",
    "🌙 風花舞い、過去と未来を繋ぐ。",
    "🌗 夢の跡、月だけがすべてを見ていた。",
    "🌖 泡沫のごとく、想いは昇華す。",
    "🌔 白露落ち、記憶の舟は岸を離る。",
    "🌑 見えぬものこそ、心を照らす。",
]
FORTUNES = [
    "🌟 今日の運勢：大吉 — 万事順調、心静如水。",
    "🌞 今日の運勢：中吉 — 有收获，但需谨慎行事。",
    "🌤️ 今日の運勢：小吉 — 细雨润物，蓄势待发。",
    "🌫️ 今日の運勢：末吉 — 运转微妙，勿急勿躁。",
    "🌧️ 今日の運勢：凶 — 凡事不强求，静观其变。",
]


def make_block(day: date) -> str:
    seed = hashlib.sha256(day.isoformat().encode("ascii")).digest()
    quote = QUOTES[int.from_bytes(seed[:4], "big") % len(QUOTES)]
    fortune = FORTUNES[int.from_bytes(seed[4:8], "big") % len(FORTUNES)]
    return "\n".join((
        START,
        '<div align="center">',
        f"  <strong>{quote}</strong><br>",
        "  <sub>☾ ─── ✦ ─── ☽</sub><br>",
        f"  {fortune}<br>",
        f"  <sub>🗓️ {day.isoformat()}</sub>",
        "</div>",
        END,
    ))


def replace_block(content: str, block: str) -> str:
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError("README must contain exactly one daily-fortune start and end marker")
    start_at = content.index(START)
    end_at = content.index(END)
    if start_at >= end_at:
        raise ValueError("daily-fortune markers are out of order")
    # Include the full lines containing the markers, preserving surrounding content.
    line_start = content.rfind("\n", 0, start_at) + 1
    end_line_end = content.find("\n", end_at)
    if end_line_end == -1:
        end_line_end = len(content)
    else:
        end_line_end += 1
    return content[:line_start] + block + "\n" + content[end_line_end:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--date", help="Override local date (YYYY-MM-DD), primarily for testing")
    args = parser.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo(args.timezone)).date()
    path = args.readme
    original = path.read_text(encoding="utf-8")
    updated = replace_block(original, make_block(day))
    if updated != original:
        path.write_text(updated, encoding="utf-8", newline="\n")
        print(f"Updated daily check-in for {day.isoformat()} ({args.timezone})")
    else:
        print(f"Daily check-in already current for {day.isoformat()}")


if __name__ == "__main__":
    main()
