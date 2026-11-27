"""한 날짜치 '신문'을 저장합니다: 지난 이야기·3줄 브리핑을 붙이고 용어 사전·날짜 목록을 갱신.

외부 라이브러리 없이 동작해서, RSS+API 방식(run.py)과 Claude 예약 작업 방식(build.py) 모두 이걸 씁니다.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from . import config
from .enrich import archive_dir, build_briefing, link_related, load_past, update_dates, update_glossary

log = logging.getLogger("easynews")


def save_edition(cards: list[dict], collected: int, now: datetime, quiz: list[dict] | None = None) -> dict:
    out_dir = config.OUTPUT_DIR
    today = now.strftime("%Y-%m-%d")
    os.makedirs(archive_dir(out_dir), exist_ok=True)

    link_related(cards, load_past(out_dir, today))
    payload = {
        "site": "쉽게말해",
        "date": today,
        "generated_at": now.isoformat(timespec="minutes"),
        "categories": [{"id": k, "name": v} for k, v in config.CATEGORIES.items()],
        "stats": {"collected": collected, "cards": len(cards)},
        "briefing": build_briefing(cards),
        "quiz": quiz or [],
        "cards": cards,
    }
    for path in (os.path.join(out_dir, "news.json"), os.path.join(archive_dir(out_dir), f"{today}.json")):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    n_terms = update_glossary(out_dir, cards, today)
    update_dates(out_dir)
    log.info("저장 완료: 카드 %d장, 퀴즈 %d문제, 용어 %d개", len(cards), len(payload["quiz"]), n_terms)
    return payload
