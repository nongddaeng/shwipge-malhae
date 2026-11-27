# 쉽게말해 아침판 만들기 (Claude 예약 작업용 작업 지침)

매일 아침 Claude 예약 작업이 이 문서를 그대로 따라 그날의 '쉽게말해'를 발행합니다.
사람이 직접 돌리고 싶을 때도 Claude에게 "ops/morning-edition.md 대로 오늘 아침판 만들어줘"라고 하면 됩니다.

- 저장소: `nongddaeng/shwipge-malhae` (main 브랜치)
- 사이트: https://nongddaeng.github.io/shwipge-malhae/
- 결과물: `docs/data/` 아래 JSON (사이트가 이것만 읽음)

---

## 0. 준비

1. 저장소를 push 권한으로 연결하고(`add_repo`, access=push) `/home/claude/shwipge-malhae` 에 clone 합니다. 이미 있으면 `git pull --ff-only`.
2. 한국시간 오늘 날짜(YYYY-MM-DD)를 확인합니다.
3. `docs/data/archive/오늘날짜.json` 이 이미 있고 그 안에 `"sample": true` 가 없으면, 오늘 판은 이미 발행된 것이므로 **아무것도 바꾸지 말고** "이미 발행됨"이라고만 보고하고 끝냅니다. (사용자가 다시 만들라고 직접 요청한 경우만 예외)

## 1. 뉴스 고르기

분야 5개: `economy`(경제) · `society`(사회) · `politics`(정치) · `world`(국제) · `tech`(IT·과학)

- 분야마다 **최근 24시간 안에 보도된 주요 뉴스 4개**를 고릅니다(최소 3개). 사실을 충분히 확인할 수 없거나, 쟁점 기사인데 양쪽 주장을 공정하게 쓸 자료가 부족하면 그 분야를 비워도 됩니다(빈 분야는 사이트에 '소식 없음'으로 표시됨).
- **1차: 언론사 RSS를 WebFetch로 읽습니다.** (웹 검색은 지난 해 기사가 섞여 나와 1차로 쓰지 않습니다)
  각 피드에서 제목·링크·발행 시각을 모읍니다. 읽히지 않는 피드는 건너뜁니다. 2026-11-27 기준 한국경제·SBS 피드는 정상, 경향 피드는 갱신이 멈춰 있었습니다.

  | 분야 | 한국경제 | SBS |
  |---|---|---|
  | 경제 | https://www.hankyung.com/feed/economy | https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02&plink=RSSREADER |
  | 사회 | https://www.hankyung.com/feed/society | https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03&plink=RSSREADER |
  | 정치 | https://www.hankyung.com/feed/politics | https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER |
  | 국제 | https://www.hankyung.com/feed/international | https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=07&plink=RSSREADER |
  | IT·과학 | https://www.hankyung.com/feed/it | https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08&plink=RSSREADER |

- 2026-11-27 확인: SBS 피드는 분야 번호와 상관없이 같은 종합 목록을 주고(한 번만 읽으면 됨), 한국경제 정치 피드는 갱신이 하루 이상 늦을 수 있습니다. 피드의 설명이 짧으면 제목만으로 내용을 지어내지 말고 아래 검색으로 사실을 확인합니다.
- **검색 요령:** `mode: "extended"` 에 **연·월·일을 모두 넣은 검색어**(예: `한국은행 기준금리 2026년 11월 26일`)를 씁니다. 날짜 없이 검색하면 지난 해 기사가 섞여 나옵니다.
- **2차: 고른 사건마다 웹 검색 1번**(사건 핵심어 + 오늘 날짜)으로 같은 사건을 다룬 다른 언론사 기사를 찾아 출처를 보탭니다. 검색 결과의 날짜가 오늘·어제가 아니면 쓰지 않습니다. 전체 검색은 20번 안팎으로 끝냅니다.
- **여러 언론사가 함께 다룬 사건**을 우선합니다. 한 언론사 단독 기사, 칼럼·사설·광고성 기사, 연예·스포츠 가십은 고르지 않습니다.
- **같은 사건은 카드 하나로** 묶습니다. 신문사만 다르고 내용이 같으면 출처 목록에만 추가합니다. 같은 사건을 두 분야에 넣지 않습니다(가장 잘 맞는 분야 하나).
- 날짜를 꼭 확인합니다. 어제 아침보다 오래된 기사는 고르지 않습니다. 날짜가 불분명하면 기사를 열어(WebFetch) 확인합니다.
- 기사 본문은 내용 확인이 꼭 필요할 때만 엽니다(전체 10번 이내).

### 출처 규칙
- 카드마다 출처 1~4개: `{"name": 언론사 한글 이름, "title": 기사 제목, "url": 기사 주소}`.
- **검색 결과나 실제로 연 페이지에서 본 주소만** 씁니다. 주소를 추측해서 만들지 않습니다.
- 같은 언론사는 한 번만. 가능하면 서로 다른 성향의 언론사를 섞습니다.

## 2. 카드 쓰기

독자는 **뉴스가 어렵게 느껴지는 일반 성인**입니다. '중학생 수준'은 낱말 난이도 기준일 뿐입니다.

| 항목 | 규칙 |
|---|---|
| `headline` | 사건을 담은 중립적인 한 줄 제목, 40자 이내, 언론사 꼬리표([단독] 등) 없이, 기사 제목을 그대로 베끼지 않기 |
| `keywords` | 핵심 키워드 2~4개, 각 2~8자 명사 (`#` 없이) |
| `summary` | **요약(원본 버전)**: 신문 기사 문체 3~4문장, 육하원칙 중심 |
| `easy_summary` | **쉽게 말해**: 4~6문장, '~해요'체. 전문용어는 풀어서, 비유는 1개까지. '무슨 일인지'에 집중 |
| `one_liner` | 3줄 브리핑용 한 줄, 35자 이내, 쉬운 말, '~했어요/~해요'로 끝 |
| `why_me` | **이게 나랑 무슨 상관?**: 보통 사람의 돈·생활·일·안전에 주는 영향 1~2문장. 근거 있는 것만, 단정 대신 '~할 수 있어요'. 관련이 거의 없으면 빈 문자열 `""` |
| `terms` | 기사 속 어려운 말 0~3개 `{"word", "meaning"}`, 뜻은 한 문장 쉬운 말 |
| `published` | 가장 이른 보도 시각을 알면 `2026-11-28T05:10:00+09:00` 형식, 모르면 생략 |

반드시 지킬 것:
- **기사에 없는 내용을 지어내지 않습니다.** 숫자·이름·날짜는 기사 그대로. 확실하지 않으면 빼기.
- **기사 문장을 베끼지 않고** 새 문장으로 씁니다. 따옴표 인용은 꼭 필요할 때 짧게(15자 안팎) 한 번까지.
- 의견과 사실을 구분합니다. 평가는 "~라는 비판/분석이 나왔다"처럼 누구의 말인지 밝힙니다.
- 정치·사회 쟁점은 **어느 편도 들지 않습니다.** 맞서는 주장이 있으면 양쪽을 같은 무게로 짧게 소개합니다.
- 독자를 학생·아이로 가정하는 표현 금지(형·누나, 친구들, 부모님께, 등굣길, 학교에서, 여러분도 커서 등). 가르치듯 내려다보는 말투 금지.
- 사건·사고 기사는 피해자를 존중하고 자극적인 묘사를 하지 않습니다.

## 3. 퀴즈 3문제

- 많이 보도된 카드들 중 **서로 다른 카드 3개**에서 하나씩, 4지선다.
- 카드 내용만으로 정답을 확실히 고를 수 있어야 합니다. 숫자 맞히기보다 '무슨 일/왜'를 묻습니다. 정답 위치는 골고루.
- `card` 는 아래 JSON의 `cards` 배열 순번(0부터).

## 4. 발행

1. 아래 형식으로 `/tmp/edition.json` 을 씁니다. `collected` 는 훑어본 서로 다른 기사 수(대략).

```json
{
  "collected": 120,
  "cards": [
    {
      "category": "economy",
      "headline": "...", "keywords": ["...", "..."],
      "summary": "...", "easy_summary": "...", "one_liner": "...", "why_me": "...",
      "terms": [{"word": "...", "meaning": "..."}],
      "sources": [{"name": "연합뉴스", "title": "...", "url": "https://..."}]
    }
  ],
  "quiz": [
    {"card": 0, "question": "...", "options": ["...", "...", "...", "..."], "answer": 1, "explanation": "..."}
  ]
}
```

2. 검사: `cd /home/claude/shwipge-malhae && python -m scraper.build /tmp/edition.json --check`
   경고가 나오면 해당 카드를 고친 뒤 다시 검사합니다.
3. 발행: `python -m scraper.build /tmp/edition.json`
4. 확인: `python -m pytest -q tests` 가 통과하고, `docs/data/news.json` 의 `date` 가 오늘인지 봅니다.
5. 커밋·푸시 (`docs/data` 만):
   ```
   git config user.name "쉽게말해 아침판"
   git config user.email "nongddaeng@users.noreply.github.com"
   git add docs/data
   git commit -m "아침판 YYYY-MM-DD"
   git -c push.negotiate=true push origin main
   ```
   push 가 거절되면 `git pull --rebase origin main` 후 한 번만 다시 push 합니다.

## 5. 보고

마지막에 짧게 보고합니다: 발행 여부, 분야별 카드 수, 오늘의 3줄, 문제가 있었다면 무엇이었는지.
코드나 디자인 파일은 이 작업에서 고치지 않습니다(`docs/data` 만 바꿈).
