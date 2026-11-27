import json
import os
from datetime import datetime, timedelta, timezone

from scraper import build, config

NOW = datetime(2026, 11, 28, 5, 50, tzinfo=timezone(timedelta(hours=9)))


def raw(cat="economy", head="한국은행 기준금리 동결", url="https://a.example/1", **kw):
    c = {
        "category": cat, "headline": head, "keywords": ["기준금리", "한국은행"],
        "summary": "요약", "easy_summary": "쉬운 설명", "one_liner": "한 줄", "why_me": "",
        "terms": [{"word": "기준금리", "meaning": "뜻"}],
        "sources": [{"name": "연합뉴스", "title": "t", "url": url}, {"name": "연합뉴스", "url": "https://dup"}],
    }
    c.update(kw)
    return c


def test_cleans_and_orders_cards():
    data = {"cards": [
        raw("world", "유엔 기후회의 폐막", "https://w/1"),
        raw("economy", "물가 2%대", "https://e/2", sources=[
            {"name": "A", "url": "https://e/2"}, {"name": "B", "url": "https://e/3"}]),
        raw("economy", "한국은행 기준금리 동결", "https://e/1"),
        raw("bogus"),
        raw("economy", "한국은행 기준금리 동결", "https://e/9"),  # 같은 제목 → 중복
        raw("society", "키워드 부족", "https://s/1", keywords=["하나"]),
    ]}
    cards, idx, warns = build.build_cards(data, NOW)
    assert [c["headline"] for c in cards] == ["물가 2%대", "한국은행 기준금리 동결", "유엔 기후회의 폐막"]
    assert len(cards[1]["sources"]) == 1  # 같은 언론사 중복 출처 제거
    assert idx[4] == idx[2]  # 중복 카드를 가리키는 퀴즈도 살아남도록
    assert len(warns) == 3


def test_quiz_maps_card_index_to_id():
    data = {"cards": [raw()], "quiz": [
        {"card": 0, "question": "Q?", "options": ["a", "b", "c", "d"], "answer": 2, "explanation": "e"},
        {"card": 5, "question": "Q?", "options": ["a", "b", "c", "d"], "answer": 0},
        {"card": 0, "question": "Q?", "options": ["a", "b"], "answer": 0},
    ]}
    cards, idx, warns = build.build_cards(data, NOW)
    quiz = build.build_quiz(data, idx, warns)
    assert len(quiz) == 1 and quiz[0]["card_id"] == cards[0]["id"] and quiz[0]["answer"] == 2


def test_purge_samples_then_publish(tmp_path, monkeypatch):
    d = tmp_path / "data"
    (d / "archive").mkdir(parents=True)
    for name, body in [("news.json", {"sample": True}), ("archive/2026-11-27.json", {"sample": True, "cards": []}),
                       ("glossary.json", []), ("dates.json", ["2026-11-27"])]:
        (d / name).write_text(json.dumps(body), encoding="utf-8")
    monkeypatch.setattr(config, "OUTPUT_DIR", str(d))
    assert build.purge_samples(str(d)) is True
    assert os.listdir(d / "archive") == [] and not (d / "glossary.json").exists()

    cards, idx, warns = build.build_cards({"cards": [raw()]}, NOW)
    from scraper.edition import save_edition
    save_edition(cards, 10, NOW)
    news = json.loads((d / "news.json").read_text(encoding="utf-8"))
    assert news["date"] == "2026-11-28" and "sample" not in news
    assert json.loads((d / "dates.json").read_text()) == ["2026-11-28"]
    assert build.purge_samples(str(d)) is False  # 실제 데이터는 건드리지 않음
