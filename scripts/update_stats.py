#!/usr/bin/env python3
"""Render a self-hosted language card for the profile README.

The card is a plain SVG committed to ``assets/`` so the README never depends on
a third-party image service.  It is refreshed by the daily GitHub Action.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

API = "https://api.github.com"
BAR_X, BAR_Y, BAR_W, BAR_H = 56, 118, 888, 26
COLUMNS = (56, 336, 616)
ROW_Y = (196, 236)

# Night-sky palette; light enough to read on the dark card.
COLORS = (
    "#9B87E8",  # violet
    "#F3C97B",  # gold
    "#7FC8E8",  # sky
    "#9BE0C2",  # mint
    "#F09AC0",  # pink
    "#B9B2D8",  # lavender grey
    "#6E6A8F",  # slate
)


def api_get(path: str, token: str | None) -> object:
    request = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "qimin-shen-profile-card",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def human_bytes(size: int) -> str:
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} GB"
    if size >= 1024**2:
        return f"{size / 1024**2:.1f} MB"
    return f"{size / 1024:.1f} KB"


def collect(user: str, token: str | None) -> dict:
    repos = [r for r in api_get(f"/users/{user}/repos?per_page=100&type=owner", token) if not r.get("fork")]
    totals: dict[str, int] = {}
    for repo in repos:
        for lang, size in api_get(f"/repos/{user}/{repo['name']}/languages", token).items():
            totals[lang] = totals.get(lang, 0) + int(size)

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    top = ranked[:5]
    other = sum(size for _, size in ranked[5:])
    if other:
        top.append(("Other", other))

    total = sum(totals.values())
    return {
        "repos": len(repos),
        "languages": len(totals),
        "bytes": total,
        "top": [
            {"name": name, "bytes": size, "pct": (size / total * 100) if total else 0.0}
            for name, size in top
        ],
    }


def render(data: dict, day: date) -> str:
    top = data["top"]

    # Bar geometry: accumulate exact widths, then close the rounding gap at the end.
    segments: list[str] = []
    separators: list[str] = []
    cursor = 0.0
    previous = 0.0
    for index, lang in enumerate(top):
        width = BAR_W * lang["bytes"] / data["bytes"]
        if index == len(top) - 1:
            width = BAR_W - cursor
        x = BAR_X + cursor
        color = COLORS[index % len(COLORS)]
        segments.append(f'<rect x="{x:.2f}" y="{BAR_Y}" width="{width:.2f}" height="{BAR_H}" fill="{color}"/>')
        if index and width > 6 and previous > 6:
            separators.append(f'<line x1="{x:.2f}" y1="{BAR_Y}" x2="{x:.2f}" y2="{BAR_Y + BAR_H}"/>')
        previous = width
        cursor += width

    chips: list[str] = []
    for index, lang in enumerate(top):
        column, row = index % 3, index // 3
        x, y = COLUMNS[column], ROW_Y[row]
        color = COLORS[index % len(COLORS)]
        chips.append(
            f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{color}"/>'
            f'<text x="{x + 18}" y="{y}" fill="#DCD3F2" font-size="13">{escape(lang["name"])}</text>'
            f'<text x="{x + 250}" y="{y}" fill="#9488B8" font-size="12" text-anchor="end">{lang["pct"]:.1f}%</text>'
        )

    summary = (
        f'{data["repos"]} 个公开仓库 · {data["languages"]} 种语言 · {human_bytes(data["bytes"])}'
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="300" viewBox="0 0 1000 300" role="img" aria-labelledby="stats-title stats-desc">
  <title id="stats-title">GitHub 星轨 · 语言光谱</title>
  <desc id="stats-desc">{escape(summary)}</desc>

  <defs>
    <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101226"/>
      <stop offset=".55" stop-color="#171633"/>
      <stop offset="1" stop-color="#241E45"/>
    </linearGradient>
    <clipPath id="bar"><rect x="{BAR_X}" y="{BAR_Y}" width="{BAR_W}" height="{BAR_H}" rx="13"/></clipPath>
  </defs>

  <rect width="1000" height="300" rx="26" fill="url(#card)"/>
  <rect x=".5" y=".5" width="999" height="299" rx="25.5" fill="none" stroke="#453A6D" stroke-opacity=".75"/>

  <text x="56" y="58" fill="#F2E9FF" font-size="21" font-weight="600" letter-spacing="1.5">✦ 语言光谱</text>
  <text x="56" y="86" fill="#A294C9" font-size="12" letter-spacing="2.4">LANGUAGE SPECTRUM · 星の軌跡</text>
  <text x="944" y="58" fill="#B7A8D8" font-size="12" text-anchor="end" letter-spacing="1.2">{escape(summary)}</text>
  <text x="944" y="86" fill="#7F739E" font-size="11" text-anchor="end" letter-spacing="1.6">UPDATED {day.isoformat()}</text>

  <g clip-path="url(#bar)">
    {''.join(segments)}
  </g>
  <g stroke="#171633" stroke-width="1.5" opacity=".55">
    {''.join(separators)}
  </g>

  {''.join(chips)}

  <line x1="56" y1="270" x2="944" y2="270" stroke="#3B3260" stroke-opacity=".7"/>
  <text x="56" y="288" fill="#7A6F9B" font-size="10.5" letter-spacing="1.4">AUTO-REFRESHED DAILY · 每日自动更新</text>
  <text x="944" y="288" fill="#7A6F9B" font-size="10.5" text-anchor="end" letter-spacing="1.4">星屑を集めて、今日を飾る。</text>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default="Qimin-Shen")
    parser.add_argument("--out", type=Path, default=Path("assets/github-stats.svg"))
    parser.add_argument("--date", help="Override the rendered date (YYYY-MM-DD)")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when the API fails")
    args = parser.parse_args()

    try:
        data = collect(args.user, args.token)
        if not data["bytes"]:
            raise ValueError("no language data returned")
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
        print(f"::warning::Could not refresh GitHub stats: {error}", file=sys.stderr)
        if args.strict:
            raise SystemExit(1)
        return

    day = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo(args.timezone)).date()
    svg = render(data, day)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp = args.out.with_suffix(".tmp")
    temp.write_text(svg, encoding="utf-8", newline="\n")
    temp.replace(args.out)
    print(f"Updated {args.out} ({data['repos']} repos, {data['languages']} languages)")


if __name__ == "__main__":
    main()
