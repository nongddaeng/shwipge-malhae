"""매일 아침 실행: 수집 → 중복 묶기 → 요약 → docs/data/news.json 저장

사용법:
    python -m scraper.run               # 전체 실행
    python -m scraper.run --check-feeds # RSS 주소가 살아있는지만 확인
    python -m scraper.run --no-ai       # API 없이 수집·중복제거만 테스트
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import config
from .edition import save_edition
from .dedup import cluster, group_category, merge_groups, rank, representative
from .fetch import fetch_all, fetch_body
from .summarize import Summarizer, fallback_card

KST = timezone(timedelta(hours=9))
log = logging.getLogger("easynews")


def build_cards(groups, summarizer: Summarizer | None) -> list[dict]:
    def one(group):
        group = sorted(group, key=lambda a: a.published)
        rep = representative(group)
        if config.FETCH_BODY and summarizer:
            rep.body = fetch_body(rep.link)
        if summarizer:
            try:
                card = summarizer.summarize([rep] + [a for a in group if a is not rep])
            except Exception as exc:
                log.warning("요약 실패 → 기본 카드 사용: %s", exc)
                card = fallback_card(group)
        else:
            card = fallback_card(group)

        sources, seen = [], set()
        for a in group:
            if a.source in seen:
                continue
            seen.add(a.source)
            sources.append({"name": a.source, "title": a.title, "url": a.link})

        return {
            "id": hashlib.md5(rep.link.encode()).hexdigest()[:10],
            "category": group_category(group),
            **card,
            "sources": sources,
            "published": datetime.fromtimestamp(max(a.published for a in group), KST).isoformat(),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one, groups))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-feeds", action="store_true")
    ap.add_argument("--no-ai", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    articles, report = fetch_all(config.FEEDS, config.LOOKBACK_HOURS)
    if args.check_feeds:
        for k, v in report.items():
            print(f"{'✅' if isinstance(v, int) and v > 0 else '⚠️ '} {k}: {v}")
        return 0
    log.info("수집한 기사: %d건", len(articles))
    if not articles:
        log.error("기사를 하나도 못 가져왔어요. --check-feeds 로 피드를 확인하세요.")
        return 1

    summarizer = None if args.no_ai else Summarizer(config.MODEL)

    groups = cluster(articles, config.DEDUP_THRESHOLD)
    log.info("1차 중복 묶기: %d건 → %d개 묶음", len(articles), len(groups))

    # 카테고리별 상위 후보만 추려서 AI 2차 묶기 → 최종 선정
    selected = []
    for cat in config.CATEGORIES:
        cands = rank([g for g in groups if group_category(g) == cat])[: config.TOP_N_PER_CATEGORY * 3]
        if summarizer and config.LLM_MERGE:
            sets = summarizer.find_same_events([representative(g).title for g in cands])
            before = len(cands)
            cands = merge_groups(cands, sets)
            log.info("[%s] AI 2차 묶기: %d → %d", cat, before, len(cands))
        selected.extend(rank(cands)[: config.TOP_N_PER_CATEGORY])

    cards = build_cards(selected, summarizer)
    # 2차 묶기로 카테고리가 바뀐 경우까지 반영해 카테고리별 순서 유지
    order = {c: i for i, c in enumerate(config.CATEGORIES)}
    cards.sort(key=lambda c: (order.get(c["category"], 99), -len(c["sources"])))

    quiz = []
    if summarizer:
        top = sorted(cards, key=lambda c: len(c["sources"]), reverse=True)[:8]
        quiz = summarizer.make_quiz(top)
    save_edition(cards, len(articles), datetime.now(KST), quiz=quiz)
    return 0


if __name__ == "__main__":
    sys.exit(main())
