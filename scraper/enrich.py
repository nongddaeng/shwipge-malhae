"""오늘 카드에 덧붙이는 것들: 지난 이야기 연결, 3줄 브리핑, 용어 사전, 날짜 목록."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

from .dedup import bigrams, cosine


# ── 지난 날짜 파일 ──────────────────────────────────────────────

def archive_dir(output_dir: str) -> str:
    return os.path.join(output_dir, "archive")


def load_past(output_dir: str, today: str, days: int = 14) -> list[tuple[str, dict]]:
    """오늘을 뺀 최근 며칠치 카드를 (날짜, 카드) 목록으로 읽어옵니다. 최신순."""
    d0 = date.fromisoformat(today)
    out = []
    for i in range(1, days + 1):
        day = (d0 - timedelta(days=i)).isoformat()
        path = os.path.join(archive_dir(output_dir), f"{day}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                for c in json.load(f).get("cards", []):
                    out.append((day, c))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def update_dates(output_dir: str) -> list[str]:
    """archive 폴더에 있는 날짜 목록(최신순)을 dates.json으로 저장합니다."""
    days = sorted(
        (f[:-5] for f in os.listdir(archive_dir(output_dir)) if f.endswith(".json")),
        reverse=True,
    )
    with open(os.path.join(output_dir, "dates.json"), "w", encoding="utf-8") as f:
        json.dump(days, f, ensure_ascii=False)
    return days


# ── 지난 이야기 연결 ────────────────────────────────────────────

def story_score(a: dict, b: dict) -> float:
    """두 카드가 '이어지는 이야기'인지 점수 (제목 유사도 + 키워드 겹침)."""
    title = cosine(bigrams(a.get("headline", "")), bigrams(b.get("headline", "")))
    ka, kb = set(a.get("keywords") or []), set(b.get("keywords") or [])
    kw = len(ka & kb) / len(ka | kb) if ka and kb else 0.0
    return 0.55 * title + 0.45 * kw


def link_related(cards: list[dict], past: list[tuple[str, dict]], threshold: float = 0.33, limit: int = 3) -> None:
    for c in cards:
        hits = []
        for day, p in past:
            s = story_score(c, p)
            if s >= threshold:
                hits.append((day, s, p))
        # 날짜마다 가장 비슷한 것 하나만, 최신순으로
        best: dict[str, tuple[float, dict]] = {}
        for day, s, p in hits:
            if day not in best or s > best[day][0]:
                best[day] = (s, p)
        c["related"] = [
            {"date": day, "id": p["id"], "headline": p["headline"]}
            for day, (s, p) in sorted(best.items(), reverse=True)[:limit]
        ]


# ── 3줄 브리핑 ──────────────────────────────────────────────────

def build_briefing(cards: list[dict], n: int = 3) -> list[dict]:
    """가장 많은 언론사가 다룬 뉴스 n개 (한 분야에 몰리지 않게 분야당 최대 2개)."""
    ranked = sorted(cards, key=lambda c: len(c.get("sources", [])), reverse=True)
    out, per_cat = [], {}
    for c in ranked:
        if per_cat.get(c["category"], 0) >= 2:
            continue
        per_cat[c["category"]] = per_cat.get(c["category"], 0) + 1
        out.append({"id": c["id"], "category": c["category"], "text": c.get("one_liner") or c["headline"]})
        if len(out) == n:
            break
    return out


# ── 용어 사전 ───────────────────────────────────────────────────

def update_glossary(output_dir: str, cards: list[dict], today: str, max_refs: int = 5) -> int:
    """카드의 '어려운 말'을 모아 glossary.json에 쌓습니다. 뜻풀이는 가장 최근 것으로."""
    path = os.path.join(output_dir, "glossary.json")
    try:
        with open(path, encoding="utf-8") as f:
            items = {g["word"]: g for g in json.load(f)}
    except (OSError, json.JSONDecodeError):
        items = {}

    for c in cards:
        for t in c.get("terms") or []:
            word = (t.get("word") or "").strip()
            meaning = (t.get("meaning") or "").strip()
            if not word or not meaning:
                continue
            g = items.setdefault(word, {"word": word, "meaning": meaning, "refs": []})
            g["meaning"] = meaning
            ref = {"date": today, "id": c["id"], "headline": c["headline"]}
            g["refs"] = [ref] + [r for r in g["refs"] if not (r["date"] == today and r["id"] == c["id"])]
            g["refs"] = g["refs"][:max_refs]

    ordered = sorted(items.values(), key=lambda g: g["word"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=1)
    return len(ordered)
