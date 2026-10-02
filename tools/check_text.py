#!/usr/bin/env python3
"""docs/ 텍스트 무결성 검사기.

한국어 문서에 섞여 들어간 중국어 문자, U+FFFD(치환 문자),
깨진 코드펜스, 표 열 수 불일치를 찾아낸다.

사용법:
  python3 tools/check_text.py           # 검사만 (위반 시 exit 1)
  python3 tools/check_text.py --quiet   # 위반 없으면 출력 없음

왜 필요한가:
  한국어 작업 중 손으로 편집하면 CJK 문자 혼입과 코드펜스 실수가 반복된다.
  두 사례 모두 사람이 읽을 때는 눈에 잘 안 띈다.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
ROOT = Path(__file__).resolve().parent.parent
FILES = sorted(DOCS.glob("*.md")) + [ROOT / "AGENTS.md"]

HANGUL = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")
CJK = re.compile(
    r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef]"
)
REPLACEMENT = "\ufffd"
PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b|\?\?\?|작성 예정")
TABLE_RULE = re.compile(r"^\|[\s:\-|]+\|$")
PROHIBITION_DECLARATION = re.compile(r"금지|남기지 않는다|사용하지 않는다")


def unescaped_pipes(line: str) -> int:
    """이스케이프된 `\\|`를 제외한 파이프 수."""
    return len(re.findall(r"(?<!\\)\|", line))


def check() -> list[str]:
    problems: list[str] = []
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        rel = path.name

        # 1) 중국어 문자 혼입 (한글이 아닌 CJK)
        cjk = Counter(c for c in text if CJK.match(c) and not HANGUL.match(c))
        for ch, n in cjk.most_common():
            problems.append(
                f"{rel}: 한국어 문장에 중국어 문자 {ch!r}(U+{ord(ch):04X}) {n}회 — "
                f"HANGUL 영역이 아닌 CJK는 금지"
            )

        # 2) 치환 문자 — 인코딩 손실의 증거
        n_bad = text.count(REPLACEMENT)
        if n_bad:
            for i, line in enumerate(lines, 1):
                if REPLACEMENT in line:
                    problems.append(f"{rel}:{i}: U+FFFD 치환 문자 — 인코딩 손실")

        # 3) 코드펜스 균형. 홀수면 렌더가 깨진다.
        fences = sum(1 for line in lines if line.startswith("```"))
        if fences % 2:
            problems.append(
                f"{rel}: 코드펜스 {fences}개(홀수) — 닫히지 않은 블록이 있음"
            )

        # 4) 표 열 수 불일치 (이스케이프된 파이프는 무시)
        i = 0
        while i < len(lines):
            if lines[i].startswith("|") and i + 1 < len(lines) and TABLE_RULE.match(lines[i + 1]):
                expected = unescaped_pipes(lines[i])
                j = i
                while j < len(lines) and lines[j].startswith("|"):
                    if not TABLE_RULE.match(lines[j]) and unescaped_pipes(lines[j]) != expected:
                        problems.append(
                            f"{rel}:{j + 1}: 표 열 수 {unescaped_pipes(lines[j])} "
                            f"≠ 헤더 {expected}"
                        )
                    j += 1
                i = j
            else:
                i += 1

        # 5) 금지된 표식
        for i, line in enumerate(lines, 1):
            if PLACEHOLDER.search(line) and not PROHIBITION_DECLARATION.search(line):
                problems.append(f"{rel}:{i}: 금지 표식 — {line.strip()[:60]}")

    return problems


def main() -> int:
    quiet = "--quiet" in sys.argv
    problems = check()
    if not problems:
        if not quiet:
            print(f"OK — {len(FILES)}개 문서, 위반 0건")
        return 0
    for p in problems:
        print(f"  {p}")
    print(f"\n위반 {len(problems)}건 (파일 {len(FILES)}개 검사)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
