"""쉽게말해 설정 파일 — 카테고리, 언론사 RSS, 개수 등을 여기서 바꿉니다."""

import os

# 탭에 보일 카테고리 (순서대로 노출)
CATEGORIES = {
    "economy": "경제",
    "society": "사회",
    "politics": "정치",
    "world": "국제",
    "tech": "IT·과학",
}

# 카테고리별 RSS 피드. 언론사가 주소를 바꾸면 여기만 고치면 됩니다.
# `python -m scraper.run --check-feeds` 로 살아있는 피드를 확인할 수 있어요.
FEEDS = {
    "economy": [
        ("연합뉴스", "https://www.yna.co.kr/rss/economy.xml"),
        ("한국경제", "https://www.hankyung.com/feed/economy"),
        ("경향신문", "https://www.khan.co.kr/rss/rssdata/economy_news.xml"),
        ("한겨레", "https://www.hani.co.kr/rss/economy/"),
        ("동아일보", "https://rss.donga.com/economy.xml"),
        ("SBS", "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02&plink=RSSREADER"),
    ],
    "society": [
        ("연합뉴스", "https://www.yna.co.kr/rss/society.xml"),
        ("한국경제", "https://www.hankyung.com/feed/society"),
        ("경향신문", "https://www.khan.co.kr/rss/rssdata/society_news.xml"),
        ("한겨레", "https://www.hani.co.kr/rss/society/"),
        ("동아일보", "https://rss.donga.com/national.xml"),
        ("SBS", "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03&plink=RSSREADER"),
    ],
    "politics": [
        ("연합뉴스", "https://www.yna.co.kr/rss/politics.xml"),
        ("한국경제", "https://www.hankyung.com/feed/politics"),
        ("경향신문", "https://www.khan.co.kr/rss/rssdata/politic_news.xml"),
        ("한겨레", "https://www.hani.co.kr/rss/politics/"),
        ("동아일보", "https://rss.donga.com/politics.xml"),
        ("SBS", "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER"),
    ],
    "world": [
        ("연합뉴스", "https://www.yna.co.kr/rss/international.xml"),
        ("한국경제", "https://www.hankyung.com/feed/international"),
        ("경향신문", "https://www.khan.co.kr/rss/rssdata/kh_world.xml"),
        ("한겨레", "https://www.hani.co.kr/rss/international/"),
        ("동아일보", "https://rss.donga.com/international.xml"),
        ("SBS", "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=07&plink=RSSREADER"),
    ],
    "tech": [
        ("연합뉴스", "https://www.yna.co.kr/rss/industry.xml"),
        ("한국경제", "https://www.hankyung.com/feed/it"),
        ("경향신문", "https://www.khan.co.kr/rss/rssdata/science_news.xml"),
        ("한겨레", "https://www.hani.co.kr/rss/science/"),
        ("동아일보", "https://rss.donga.com/science.xml"),
    ],
}

# 최근 몇 시간 안의 기사만 모을지 (아침 6시 실행 기준, 어제 아침~오늘 아침)
LOOKBACK_HOURS = int(os.getenv("LOOKBACK_HOURS", "24"))

# 카테고리별로 보여줄 뉴스 개수
TOP_N_PER_CATEGORY = int(os.getenv("TOP_N", "8"))

# 중복 판정 기준 (0~1, 높을수록 엄격). 제목+요약의 글자 단위 유사도.
DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.42"))

# AI가 한 번 더 '같은 사건' 기사를 묶어줄지 (문자 유사도로 못 잡는 경우 보완)
LLM_MERGE = os.getenv("LLM_MERGE", "1") == "1"

# 기사 본문까지 가져와 요약 품질을 높일지 (0이면 RSS 요약문만 사용)
FETCH_BODY = os.getenv("FETCH_BODY", "1") == "1"

MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "docs/data")
