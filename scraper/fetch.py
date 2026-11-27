"""RSS에서 기사 목록을 모읍니다."""

from __future__ import annotations

import calendar
import html
import logging
import re
import time
from dataclasses import dataclass, field

import feedparser

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; EasyNewsBot/1.0; +https://github.com/)"
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


@dataclass
class Article:
    source: str
    category: str
    title: str
    link: str
    description: str
    published: float  # unix time
    body: str = ""
    extra: dict = field(default_factory=dict)


def clean(text: str) -> str:
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    return WS_RE.sub(" ", text).strip()


def _published(entry) -> float:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return float(calendar.timegm(t))
    return time.time()


def fetch_feed(source: str, url: str, category: str) -> list[Article]:
    parsed = feedparser.parse(url, agent=UA)
    if parsed.bozo and not parsed.entries:
        raise RuntimeError(f"피드 읽기 실패: {parsed.bozo_exception}")
    out = []
    for e in parsed.entries:
        title = clean(e.get("title", ""))
        link = e.get("link", "")
        if not title or not link:
            continue
        out.append(
            Article(
                source=source,
                category=category,
                title=title,
                link=link,
                description=clean(e.get("summary", ""))[:600],
                published=_published(e),
            )
        )
    return out


def fetch_all(feeds: dict, lookback_hours: int) -> tuple[list[Article], dict]:
    cutoff = time.time() - lookback_hours * 3600
    articles: list[Article] = []
    report = {}
    for category, items in feeds.items():
        for source, url in items:
            try:
                got = [a for a in fetch_feed(source, url, category) if a.published >= cutoff]
                articles.extend(got)
                report[f"{category}/{source}"] = len(got)
            except Exception as exc:  # 한 언론사 실패가 전체를 멈추지 않게
                log.warning("[%s/%s] %s", category, source, exc)
                report[f"{category}/{source}"] = f"실패: {exc}"
    return articles, report


def fetch_body(url: str, max_chars: int = 3000) -> str:
    """기사 본문을 추출합니다. 요약 입력으로만 쓰고 사이트에는 저장·노출하지 않습니다."""
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False) or ""
        return text[:max_chars]
    except Exception as exc:
        log.info("본문 추출 실패 %s: %s", url, exc)
        return ""
