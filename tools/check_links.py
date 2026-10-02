#!/usr/bin/env python3
"""docs/ 내부 링크 검증기.

GitHub 슬러그 규칙을 정확히 재현하고, 깨진 앵커를 자동 수정한다.
사용법:  python3 tools/check_links.py [--fix]
"""
from __future__ import annotations

import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
FILES = [
    "README.md",
    "00-convention.md",
    "01-architecture.md",
    "02-data-design.md",
    "03-ui-design.md",
    "04-development-plan.md",
    "PRD.md",
]
# 외부 경로(저장소 밖)는 존재를 확인할 수 없으므로 제외
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
OUTSIDE = {"../.omx/plans/prd-agent-skill-studio.md"}

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")


def github_slug(text: str) -> str:
    """GitHub 헤딩 앵커 생성 규칙.

    1. 소문자로
    2. 마크다운 인라인 문법 제거 (코드백틱, 링크 텍스트)
    3. 알파벳·숫자·공백·하이픈이 아닌 문자 제거 (유니코드 문자 유지)
    4. 공백 -> 하이픈
    """
    s = text.strip().lower()
    s = re.sub(r"`([^`]*)`", r"\1", s)              # `code`
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # [text](url)
    s = re.sub(r"[*_]{1,2}", "", s)                 # **bold** _em_
    out = []
    for ch in s:
        if ch.isalnum() or ch in " -_" or ord(ch) > 0x2E80:
            out.append(ch)
        # 그 외(괄호, 역따옴표, 기호 등)는 제거 — GitHub과 동일
    s = "".join(out)
    return s.replace(" ", "-")


def build_anchors() -> dict[str, set[str]]:
    anchors: dict[str, set[str]] = defaultdict(set)
    for name in FILES:
        text = (DOCS / name).read_text(encoding="utf-8")
        for _, raw in HEADING.findall(text):
            anchors[name].add(github_slug(raw))
    return anchors


def check(fix: bool) -> int:
    anchors = build_anchors()
    problems: list[tuple[str, str, str]] = []
    fixes: list[tuple[Path, str, str]] = []

    for name in FILES:
        path = DOCS / name
        text = path.read_text(encoding="utf-8")
        for _, url in LINK.findall(text):
            if url.startswith(EXTERNAL_PREFIXES) or url in OUTSIDE:
                continue
            target, _, frag = url.partition("#")
            target = target.removeprefix("./")
            tf = name if not target else target
            if tf not in FILES:
                problems.append((name, url, "대상 파일 없음"))
                continue
            if not frag:
                continue
            if frag in anchors[tf]:
                continue
            # 유사 앵커 탐색: 접두사/부분 일치
            cand = [a for a in anchors[tf] if a.startswith(frag[:12])]
            if len(cand) == 1:
                fixes.append((path, url, f"{target}#{cand[0]}"))
            else:
                near = sorted(anchors[tf], key=lambda a: abs(len(a) - len(frag)))[:3]
                problems.append((name, url, f"앵커 없음 (유사 후보: {near})"))

    if fix and fixes:
        for path, old, new in fixes:
            body = path.read_text(encoding="utf-8")
            path.write_text(body.replace(old, new), encoding="utf-8")
        print(f"자동 수정 {len(fixes)}건")

    print(f"앵커 집합: {sum(len(v) for v in anchors.values())}개")
    print(f"미해결 문제: {len(problems)}건")
    for name, url, why in problems:
        print(f"  [{name}] {url}\n      → {why}")
    return len(problems)


if __name__ == "__main__":
    sys.exit(1 if check("--fix" in sys.argv) else 0)
