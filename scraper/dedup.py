"""신문사만 다르고 내용이 같은 기사를 하나로 묶습니다.

1단계: 제목·요약문의 '글자 2개 묶음(bigram)' 유사도로 빠르게 묶기
       (한국어는 형태소 분석 없이도 bigram이 잘 통합니다)
2단계(선택): AI에게 대표 제목 목록을 주고 같은 사건끼리 한 번 더 묶기
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .fetch import Article

# 제목에서 유사도 계산을 방해하는 꼬리표들
NOISE_RE = re.compile(
    r"\[[^\]]*\]|【[^】]*】|\([^)]*(?:종합|속보|단독|영상|포토|사진|인터뷰)[^)]*\)|"
    r"(?:속보|단독|종합|포토|영상)\s*[:=]?"
)
PUNCT_RE = re.compile(r"[^\w가-힣]+")


def normalize(text: str) -> str:
    text = NOISE_RE.sub(" ", text)
    text = PUNCT_RE.sub("", text.lower())
    return text


def bigrams(text: str) -> Counter:
    t = normalize(text)
    return Counter(t[i : i + 2] for i in range(len(t) - 1))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b[k] for k, v in a.items() if k in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


def similarity(a: Article, b: Article, cache: dict) -> float:
    def vecs(x: Article):
        key = id(x)
        if key not in cache:
            cache[key] = (bigrams(x.title), bigrams(x.title + " " + x.description[:200]))
        return cache[key]

    (ta, fa), (tb, fb) = vecs(a), vecs(b)
    # 제목이 아주 비슷하거나, 제목+리드문이 전체적으로 비슷하면 같은 기사
    return max(cosine(ta, tb), 0.5 * cosine(ta, tb) + 0.5 * cosine(fa, fb))


class UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        self.p[self.find(a)] = self.find(b)


def cluster(articles: list[Article], threshold: float) -> list[list[Article]]:
    """비슷한 기사끼리 묶은 목록을 반환합니다. (카테고리를 넘나들어도 묶음)"""
    # 같은 링크는 먼저 제거 (한 언론사가 여러 섹션에 같은 기사를 올리는 경우)
    seen, uniq = set(), []
    for a in articles:
        key = a.link.split("?")[0]
        if key not in seen:
            seen.add(key)
            uniq.append(a)

    n = len(uniq)
    uf = UnionFind(n)
    cache: dict = {}
    for i in range(n):
        for j in range(i + 1, n):
            if similarity(uniq[i], uniq[j], cache) >= threshold:
                uf.union(i, j)

    groups: dict[int, list[Article]] = {}
    for i, a in enumerate(uniq):
        groups.setdefault(uf.find(i), []).append(a)
    return list(groups.values())


def merge_groups(groups: list[list[Article]], merge_sets: list[list[int]]) -> list[list[Article]]:
    """AI가 '같은 사건'이라고 알려준 인덱스 묶음대로 그룹을 합칩니다."""
    used = set()
    out = []
    for s in merge_sets:
        s = [i for i in s if 0 <= i < len(groups) and i not in used]
        if not s:
            continue
        merged = []
        for i in s:
            merged.extend(groups[i])
            used.add(i)
        out.append(merged)
    out.extend(g for i, g in enumerate(groups) if i not in used)
    return out


def group_category(group: list[Article]) -> str:
    """여러 섹션에 걸친 묶음은 가장 많이 실린 섹션으로 배정합니다."""
    return Counter(a.category for a in group).most_common(1)[0][0]


def representative(group: list[Article]) -> Article:
    """요약문이 가장 충실한 기사를 대표로 고릅니다."""
    return max(group, key=lambda a: (len(a.description), -a.published))


def rank(groups: list[list[Article]]) -> list[list[Article]]:
    """여러 언론사가 다룰수록 중요한 뉴스로 보고 위로 올립니다."""
    return sorted(
        groups,
        key=lambda g: (len({a.source for a in g}), max(a.published for a in g)),
        reverse=True,
    )
