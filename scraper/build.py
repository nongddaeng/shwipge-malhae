"""Claude가 매일 아침 써 준 기사 카드(JSON)를 사이트 데이터로 발행합니다.

사용법:
    python -m scraper.build edition.json            # 오늘(한국시간) 날짜로 발행
    python -m scraper.build edition.json --check    # 검사만 하고 저장하지 않음

입력 형식 (ops/morning-edition.md 참고):
{
  "collected": 140,                       # 훑어본 기사 수
  "cards": [
    {
      "category": "economy",              # economy | society | politics | world | tech
      "headline": "...", "keywords": ["...", "..."],
      "summary": "...", "easy_summary": "...", "one_liner": "...", "why_me": "...",
      "terms": [{"word": "...", "meaning": "..."}],
      "sources": [{"name": "연합뉴스", "title": "...", "url": "https://..."}],
      "published": "2026-11-28T05:10:00+09:00"   # 선택
    }
  ],
  "quiz": [
    {"card": 0, "question": "...", "options": ["...", "...", "...", "..."], "answer": 1, "explanation": "..."}
  ]
}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from . import config
from .dedup import bigrams, cosine
from .edition import save_edition
from .enrich import archive_dir

KST = timezone(timedelta(hours=9))
log = logging.getLogger("easynews")

TEXT_FIELDS = ("headline", "summary", "easy_summary", "one_liner")


class EditionError(ValueError):
    pass


def _s(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def clean_card(raw: dict, now: datetime) -> tuple[dict | None, str]:
    """카드 하나를 검사·정리합니다. (문제가 있으면 None과 이유)"""
    if not isinstance(raw, dict):
        return None, "카드가 객체가 아님"
    cat = _s(raw.get("category"))
    if cat not in config.CATEGORIES:
        return None, f"알 수 없는 분야 '{cat}'"
    card = {k: _s(raw.get(k)) for k in TEXT_FIELDS}
    missing = [k for k, v in card.items() if not v]
    if missing:
        return None, f"빈 항목 {missing}"

    kws = [_s(k).lstrip("#") for k in raw.get("keywords") or [] if _s(k)]
    if not 2 <= len(kws) <= 4:
        return None, f"키워드는 2~4개여야 함 ({len(kws)}개)"

    sources, seen = [], set()
    for s in raw.get("sources") or []:
        if not isinstance(s, dict):
            continue
        name, url = _s(s.get("name")), _s(s.get("url"))
        if not name or not url.startswith(("http://", "https://")) or name in seen:
            continue
        seen.add(name)
        sources.append({"name": name, "title": _s(s.get("title")) or card["headline"], "url": url})
    if not sources:
        return None, "출처(언론사 이름+링크)가 하나도 없음"

    terms = [
        {"word": _s(t.get("word")), "meaning": _s(t.get("meaning"))}
        for t in (raw.get("terms") or [])[:3]
        if isinstance(t, dict) and _s(t.get("word")) and _s(t.get("meaning"))
    ]
    published = _s(raw.get("published"))
    try:
        datetime.fromisoformat(published)
    except ValueError:
        published = now.isoformat(timespec="minutes")

    card.update(
        id=hashlib.md5(sources[0]["url"].encode()).hexdigest()[:10],
        category=cat,
        keywords=kws,
        why_me=_s(raw.get("why_me")),
        terms=terms,
        sources=sources,
        published=published,
    )
    return card, ""


def build_cards(data: dict, now: datetime) -> tuple[list[dict], dict[int, str], list[str]]:
    """카드 목록을 정리하고, 원래 순번→카드 id 대응표와 경고 목록을 돌려줍니다."""
    cards, index_to_id, warnings = [], {}, []
    for i, raw in enumerate(data.get("cards") or []):
        card, why = clean_card(raw, now)
        if not card:
            warnings.append(f"카드 {i} 제외: {why}")
            continue
        # 같은 사건이 두 번 들어간 경우(같은 링크 또는 거의 같은 제목) 하나만 남김
        dup = next(
            (c for c in cards
             if c["id"] == card["id"] or cosine(bigrams(c["headline"]), bigrams(card["headline"])) > 0.8),
            None,
        )
        if dup:
            warnings.append(f"카드 {i} 제외: '{dup['headline']}'와 중복")
            index_to_id[i] = dup["id"]
            continue
        index_to_id[i] = card["id"]
        cards.append(card)

    order = {c: n for n, c in enumerate(config.CATEGORIES)}
    # 분야 순서 → 많이 보도된 순 (같으면 Claude가 적은 순서 유지)
    cards = sorted(cards, key=lambda c: (order[c["category"]], -len(c["sources"])))
    return cards, index_to_id, warnings


def build_quiz(data: dict, index_to_id: dict[int, str], warnings: list[str]) -> list[dict]:
    quiz = []
    for i, q in enumerate(data.get("quiz") or []):
        try:
            opts = [_s(o) for o in q["options"]]
            ans = int(q["answer"])
            cid = index_to_id[int(q["card"])]
            if len(opts) != 4 or not all(opts) or not 0 <= ans < 4 or not _s(q["question"]):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            warnings.append(f"퀴즈 {i} 제외: 형식 오류")
            continue
        quiz.append({"card_id": cid, "question": _s(q["question"]), "options": opts,
                     "answer": ans, "explanation": _s(q.get("explanation"))})
    return quiz[:3]


def purge_samples(out_dir: str) -> bool:
    """처음 진짜 발행할 때, 화면 확인용 예시 데이터를 지웁니다."""
    path = os.path.join(out_dir, "news.json")
    try:
        with open(path, encoding="utf-8") as f:
            if not json.load(f).get("sample"):
                return False
    except (OSError, json.JSONDecodeError):
        return False
    adir = archive_dir(out_dir)
    for name in os.listdir(adir) if os.path.isdir(adir) else []:
        p = os.path.join(adir, name)
        try:
            with open(p, encoding="utf-8") as f:
                if json.load(f).get("sample"):
                    os.remove(p)
        except (OSError, json.JSONDecodeError):
            pass
    for name in ("glossary.json", "dates.json"):
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            os.remove(p)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("edition")
    ap.add_argument("--check", action="store_true", help="검사만 하고 저장하지 않음")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with open(args.edition, encoding="utf-8") as f:
        data = json.load(f)
    now = datetime.now(KST)
    cards, index_to_id, warnings = build_cards(data, now)
    quiz = build_quiz(data, index_to_id, warnings)
    for w in warnings:
        log.warning(w)

    counts = {config.CATEGORIES[c]: sum(1 for x in cards if x["category"] == c) for c in config.CATEGORIES}
    log.info("카드 %d장 %s, 퀴즈 %d문제", len(cards), counts, len(quiz))
    if len(cards) < 5:
        log.error("카드가 너무 적어요(5장 미만). 발행하지 않습니다.")
        return 1
    if args.check:
        return 0

    if purge_samples(config.OUTPUT_DIR):
        log.info("예시 데이터를 지웠어요 (첫 실제 발행)")
    collected = int(data.get("collected") or len(cards))
    save_edition(cards, collected, now, quiz=quiz)
    return 0


if __name__ == "__main__":
    sys.exit(main())
