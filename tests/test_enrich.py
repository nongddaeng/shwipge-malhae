import json
import os

from scraper.enrich import build_briefing, link_related, load_past, update_dates, update_glossary


def card(id, headline, kws, cat="economy", n=1, terms=()):
    return {
        "id": id, "headline": headline, "keywords": list(kws), "category": cat,
        "sources": [{}] * n, "one_liner": headline + " 한줄", "terms": list(terms),
    }


def write_day(d, day, cards):
    os.makedirs(os.path.join(d, "archive"), exist_ok=True)
    with open(os.path.join(d, "archive", f"{day}.json"), "w", encoding="utf-8") as f:
        json.dump({"cards": cards}, f, ensure_ascii=False)


def test_related_links_previous_days(tmp_path):
    d = str(tmp_path)
    write_day(d, "2026-11-25", [card("a", "내년도 예산안 여야 협상 시작", ["예산안", "국회"])])
    write_day(d, "2026-11-26", [card("b", "예산안 협상 난항, 복지 예산 이견", ["예산안", "국회", "복지"]),
                                card("c", "서울 아파트값 둔화", ["부동산"])])
    today = [card("t", "내년도 예산안, 처리 시한 앞두고 막판 협상", ["예산안", "국회", "본회의"], cat="politics")]
    link_related(today, load_past(d, "2026-11-27"))
    rel = today[0]["related"]
    assert [r["id"] for r in rel] == ["b", "a"]  # 최신순, 관련 없는 c 제외


def test_unrelated_not_linked(tmp_path):
    d = str(tmp_path)
    write_day(d, "2026-11-26", [card("x", "삼성전자 신형 반도체 공개", ["반도체"])])
    today = [card("t", "기준금리 동결", ["기준금리", "한국은행"])]
    link_related(today, load_past(d, "2026-11-27"))
    assert today[0]["related"] == []


def test_briefing_top3_spread_categories():
    cards = [card("1", "a", [], "economy", 5), card("2", "b", [], "economy", 4),
             card("3", "c", [], "economy", 4), card("4", "d", [], "society", 3)]
    b = build_briefing(cards)
    assert [x["id"] for x in b] == ["1", "2", "4"]
    assert b[0]["text"] == "a 한줄"


def test_glossary_accumulates(tmp_path):
    d = str(tmp_path)
    update_glossary(d, [card("1", "h1", [], terms=[{"word": "기준금리", "meaning": "뜻1"}])], "2026-11-26")
    n = update_glossary(d, [card("2", "h2", [], terms=[{"word": "기준금리", "meaning": "뜻2"},
                                                     {"word": "가계부채", "meaning": "빚"}])], "2026-11-27")
    g = {x["word"]: x for x in json.load(open(os.path.join(d, "glossary.json"), encoding="utf-8"))}
    assert n == 2 and g["기준금리"]["meaning"] == "뜻2"
    assert [r["id"] for r in g["기준금리"]["refs"]] == ["2", "1"]


def test_dates_listed_newest_first(tmp_path):
    d = str(tmp_path)
    write_day(d, "2026-11-25", [])
    write_day(d, "2026-11-27", [])
    assert update_dates(d) == ["2026-11-27", "2026-11-25"]
