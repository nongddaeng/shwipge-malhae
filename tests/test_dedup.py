import time

from scraper.dedup import cluster, group_category, rank
from scraper.fetch import Article


def A(src, title, desc="", cat="economy", link=None):
    return Article(src, cat, title, link or f"https://{src}.example/{abs(hash(title))}", desc, time.time())


def test_same_story_different_outlets_grouped():
    arts = [
        A("연합", "[속보] 한은, 기준금리 연 2.50%로 동결…3회 연속", "한국은행 금융통화위원회가 기준금리를 동결했다."),
        A("한경", "한국은행 기준금리 2.50% 동결 (종합)", "한국은행 금통위는 27일 기준금리를 연 2.50%로 유지했다."),
        A("경향", "한은 기준금리 동결, 연 2.50% 유지", "금융통화위원회가 기준금리를 연 2.50%로 동결했다."),
        A("SBS", "서울 아파트값 상승폭 3주째 둔화", "한국부동산원 주간 아파트 가격 동향에 따르면"),
        A("동아", "삼성전자 신형 반도체 공개", "삼성전자가 차세대 메모리를 선보였다.", cat="tech"),
    ]
    groups = rank(cluster(arts, 0.42))
    assert len(groups) == 3
    top = groups[0]
    assert {a.source for a in top} == {"연합", "한경", "경향"}
    assert group_category(top) == "economy"


def test_different_stories_kept_apart():
    arts = [
        A("연합", "기준금리 동결", "한은이 금리를 동결했다"),
        A("한경", "기준금리 인하 기대 커져", "시장에서는 내년 인하를 점친다"),
        A("경향", "전세사기 피해자 지원법 국회 통과", "", cat="society"),
    ]
    groups = cluster(arts, 0.42)
    assert len(groups) >= 2
    assert not any({"연합", "경향"} <= {a.source for a in g} for g in groups)


def test_duplicate_links_removed():
    arts = [A("연합", "같은 기사", link="https://x/1?a=1"), A("연합", "같은 기사", cat="society", link="https://x/1?b=2")]
    assert sum(len(g) for g in cluster(arts, 0.42)) == 1
