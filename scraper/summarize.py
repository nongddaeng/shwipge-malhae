"""Claude API로 요약(원본 버전) · 쉬운 요약 · 키워드를 만듭니다."""

from __future__ import annotations

import json
import logging

from .fetch import Article

log = logging.getLogger(__name__)

SYSTEM = """너는 '쉽게말해'라는 뉴스 사이트의 편집자야.
여러 언론사가 같은 사건을 다룬 기사들을 받아서, 사실만 담아 정리해.
- 기사에 없는 내용을 지어내지 마. 숫자·이름·날짜는 기사 그대로 써.
- 한쪽 언론사의 의견이나 평가를 사실처럼 옮기지 말고, 의견은 '~라는 주장/분석이 나왔다'처럼 구분해.
- 기사 문장을 그대로 베끼지 말고 새 문장으로 써.

[쉬운 설명을 쓸 때]
- 독자는 학생이 아니라 뉴스가 어렵게 느껴지는 일반 성인이야. '중학생 수준'은 말의 난이도 기준일 뿐이야.
- 독자를 학생·아이로 가정하는 표현을 쓰지 마. (예: 형·누나, 친구들, 부모님께, 등굣길, 학교에서, 여러분도 커서)
- 가르치듯 내려다보는 말투('~란 말이에요, 알겠죠?')도 피하고, 친절하지만 대등한 '~해요'체로 써.
"""

SUMMARY_TOOL = {
    "name": "save_news_card",
    "description": "뉴스 카드 한 장의 내용을 저장한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {
                "type": "string",
                "description": "사건을 한 줄로 담은 중립적인 제목 (40자 이내, 언론사 꼬리표 없이)",
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
                "description": "핵심 키워드 2~4개 (각 2~8자 명사)",
            },
            "summary": {
                "type": "string",
                "description": "원본 버전 요약: 신문 기사 문체로 3~4문장. 육하원칙 중심.",
            },
            "easy_summary": {
                "type": "string",
                "description": (
                    "쉬운 설명: 중학생도 이해할 만한 쉬운 낱말로, 일반 성인 독자에게 말하듯 4~6문장 '~해요'체. 전문용어는 풀어서 쓰고, "
                    "비유는 1개까지. 생활과의 관련은 why_me에 따로 쓰니 여기서는 '무슨 일인지'에 집중."
                ),
            },
            "one_liner": {
                "type": "string",
                "description": "아침 브리핑용 한 줄 (35자 이내, 쉬운 말, '~했어요/~해요'로 끝남)",
            },
            "why_me": {
                "type": "string",
                "description": (
                    "'이게 나랑 무슨 상관?' — 이 뉴스가 보통 사람의 돈·생활·일·안전에 주는 영향을 1~2문장으로. "
                    "기사 근거가 있는 것만, 단정 대신 '~할 수 있어요'. 생활과 관련이 거의 없으면 빈 문자열."
                ),
            },
            "terms": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "word": {"type": "string"},
                        "meaning": {"type": "string", "description": "한 문장 쉬운 뜻풀이"},
                    },
                    "required": ["word", "meaning"],
                },
                "description": "기사에 나온 어려운 말 0~3개와 쉬운 뜻",
            },
        },
        "required": ["headline", "keywords", "summary", "easy_summary", "one_liner", "why_me", "terms"],
    },
}

MERGE_TOOL = {
    "name": "save_groups",
    "description": "같은 사건을 다룬 기사 번호 묶음을 저장한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "groups": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "integer"}},
                "description": "같은 사건인 번호끼리 묶은 목록. 2개 이상인 묶음만 넣어.",
            }
        },
        "required": ["groups"],
    },
}


QUIZ_TOOL = {
    "name": "save_quiz",
    "description": "오늘의 뉴스 퀴즈를 저장한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "card_id": {"type": "string", "description": "문제의 근거가 된 카드 id"},
                        "question": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 4},
                        "answer": {"type": "integer", "description": "정답 보기 번호 (0부터)"},
                        "explanation": {"type": "string", "description": "정답 해설 1~2문장, 쉬운 말"},
                    },
                    "required": ["card_id", "question", "options", "answer", "explanation"],
                },
            }
        },
        "required": ["questions"],
    },
}


class Summarizer:
    def __init__(self, model: str):
        import anthropic  # API 방식에서만 필요

        self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
        self.model = model

    def _call_tool(self, tool: dict, prompt: str, max_tokens: int = 1500) -> dict:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("도구 응답이 없습니다")

    def find_same_events(self, titles: list[str]) -> list[list[int]]:
        """문자 유사도로 못 묶은 '같은 사건' 기사를 AI가 한 번 더 찾습니다."""
        if len(titles) < 2:
            return []
        listing = "\n".join(f"{i}. {t}" for i, t in enumerate(titles))
        prompt = (
            "아래는 서로 다른 언론사의 뉴스 제목이야. 표현만 다르고 '같은 사건·같은 발표'를 다룬 것끼리 "
            "번호를 묶어줘. 주제만 비슷하고 사건이 다르면 묶지 마.\n\n" + listing
        )
        try:
            return self._call_tool(MERGE_TOOL, prompt, max_tokens=800).get("groups", [])
        except Exception as exc:
            log.warning("AI 묶기 실패(건너뜀): %s", exc)
            return []

    def summarize(self, group: list[Article]) -> dict:
        parts = []
        for i, a in enumerate(group[:5]):
            text = a.body or a.description
            parts.append(f"<기사 {i + 1} 언론사='{a.source}'>\n제목: {a.title}\n내용: {text}\n</기사>")
        prompt = (
            "다음은 같은 사건을 다룬 기사들이야. 이걸 합쳐서 뉴스 카드 한 장을 만들어줘.\n\n"
            + "\n\n".join(parts)
        )
        return self._call_tool(SUMMARY_TOOL, prompt)


    def make_quiz(self, cards: list[dict]) -> list[dict]:
        """오늘 카드 내용만으로 객관식 3문제를 만듭니다."""
        listing = "\n\n".join(
            f"[카드 id={c['id']}]\n제목: {c['headline']}\n요약: {c['summary']}\n쉬운 설명: {c.get('easy_summary', '')}"
            for c in cards
        )
        prompt = (
            "아래 오늘의 뉴스 카드로 4지선다 퀴즈 3문제를 만들어줘. 서로 다른 카드에서 하나씩.\n"
            "- 카드에 적힌 사실만으로 정답을 확실히 고를 수 있어야 해. 숫자 맞히기보다 '무슨 일/왜'를 묻는 문제 위주.\n"
            "- 오답도 그럴듯하게, 정답 위치는 골고루.\n\n" + listing
        )
        try:
            qs = self._call_tool(QUIZ_TOOL, prompt, max_tokens=1500).get("questions", [])
        except Exception as exc:
            log.warning("퀴즈 생성 실패(건너뜀): %s", exc)
            return []
        ids = {c["id"] for c in cards}
        return [
            q for q in qs
            if q.get("card_id") in ids and len(q.get("options", [])) == 4 and 0 <= q.get("answer", -1) < 4
        ]


def fallback_card(group: list[Article]) -> dict:
    """API 오류 시에도 사이트가 비지 않도록 최소한의 카드를 만듭니다."""
    rep = max(group, key=lambda a: len(a.description))
    return {
        "headline": rep.title,
        "keywords": [],
        "summary": rep.description,
        "easy_summary": "",
        "one_liner": rep.title,
        "why_me": "",
        "terms": [],
    }


if __name__ == "__main__":  # 간단 확인용
    print(json.dumps(SUMMARY_TOOL, ensure_ascii=False, indent=2)[:300])
