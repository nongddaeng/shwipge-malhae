# 쉽게말해

매일 아침 경제·사회·정치·국제·IT 뉴스를 여러 언론사에서 모아, **같은 사건은 하나로 묶고**,
**신문식 요약**과 **누구나 이해할 쉬운 설명**(중학생 수준 낱말, 독자는 일반 성인)을 카드로 보여주는 사이트입니다.

## 기능

- **분야별 탭** + 카드: 키워드 → 요약(원본 버전) → 쉽게 말해(+어려운 말 풀이) → **이게 나랑 무슨 상관?** → **지난 이야기** → 보도 언론사
- **오늘 아침 3줄**: 가장 많이 보도된 뉴스 3개 (한 분야에 몰리지 않게)
- **키워드 모아보기**: 카드의 #키워드를 누르면 같은 키워드 카드만
- **지난 날짜 보기**: 상단 날짜 선택 (최근 기사와 이어지는 '지난 이야기'도 클릭하면 그날로 이동)
- **오늘의 퀴즈**: 그날 뉴스로 만든 4지선다 3문제
- **용어 사전**: 날마다 나온 어려운 말을 모아 검색
- **보기 모드**(둘 다 / 쉬운 말만 / 요약만), **글자 크기**, **다크 모드** — 브라우저에 기억됨
- **아침 알림**: 텔레그램·이메일로 3줄 브리핑 발송 (설정한 것만)

```
RSS 수집(언론사 6곳 × 5분야) → 중복 묶기(글자 유사도 + AI 2차 확인) → 많이 보도된 순 정렬
→ Claude로 요약·쉬운 요약·키워드·용어 풀이 → docs/data/news.json → GitHub Pages
```

## 폴더 구조

| 경로 | 역할 |
|---|---|
| `scraper/config.py` | 카테고리, 언론사 RSS 주소, 개수·중복 기준 등 설정 |
| `scraper/fetch.py` | RSS 수집, 본문 추출 |
| `scraper/dedup.py` | 중복 기사 묶기·순위 |
| `scraper/summarize.py` | Claude API 프롬프트(요약/쉬운 요약/키워드) |
| `scraper/enrich.py` | 지난 이야기 연결, 3줄 브리핑, 용어 사전, 날짜 목록 |
| `scraper/notify.py` | 텔레그램·이메일 아침 알림 |
| `scraper/run.py` | 전체 실행 진입점 |
| `docs/` | 웹사이트 (index.html, style.css, app.js) |
| `docs/data/` | news.json(최신), archive/날짜.json, dates.json, glossary.json |
| `.github/workflows/daily.yml` | 매일 06:00 KST 자동 실행 |

## 배포하기 (무료, 약 10분)

1. GitHub에 새 저장소를 만들고 이 폴더 내용을 그대로 올립니다.
2. **Settings → Secrets and variables → Actions → New repository secret**
   이름 `ANTHROPIC_API_KEY`, 값에 Claude API 키 (console.anthropic.com 에서 발급).
3. **Settings → Pages** → Source: *Deploy from a branch*, Branch: `main` / 폴더 `/docs` → Save.
4. **Actions 탭 → "매일 아침 뉴스 업데이트" → Run workflow** 로 첫 실행.
   몇 분 뒤 `https://<아이디>.github.io/<저장소>/` 에서 실제 뉴스가 보입니다.
   이후 매일 아침 6시에 자동으로 갱신돼요.

> 처음 올린 `docs/data/news.json` 은 화면 확인용 예시 데이터입니다. 첫 실행 때 실제 뉴스로 덮어써집니다.

## 아침 알림 설정 (선택)

먼저 **Settings → Secrets and variables → Actions → Variables** 탭에 `SITE_URL`(사이트 주소)을 넣어두면 알림에 링크가 붙어요.

**텔레그램** (가장 쉬움, 무료)
1. 텔레그램에서 `@BotFather` → `/newbot` → 이름 정하면 **봇 토큰**을 줘요.
2. 만든 봇에게 아무 메시지나 보낸 뒤, 브라우저로 `https://api.telegram.org/bot<토큰>/getUpdates` 를 열어 `"chat":{"id": 숫자` 를 찾아요.
   (여러 명이 받게 하려면 채널을 만들고 봇을 관리자로 추가 → chat id에 `@채널아이디`)
3. Secrets에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 추가.

**이메일** (지메일 예시)
1. 구글 계정 → 보안 → 2단계 인증 켜기 → **앱 비밀번호** 만들기.
2. Secrets에 `SMTP_HOST`=`smtp.gmail.com`, `SMTP_USER`=내 지메일, `SMTP_PASSWORD`=앱 비밀번호, `MAIL_TO`=받는 주소(쉼표로 여러 명).

설정하지 않은 쪽은 자동으로 건너뛰고, 알림이 실패해도 사이트 업데이트에는 영향이 없어요.
미리 보기: `python -m scraper.notify --dry-run`

## 내 컴퓨터에서 실행

```bash
pip install -r requirements.txt
python -m scraper.run --check-feeds        # RSS 주소가 살아있는지 확인
python -m scraper.run --no-ai              # API 없이 수집·중복제거만 테스트
export ANTHROPIC_API_KEY=sk-ant-...        # (Windows: set ANTHROPIC_API_KEY=...)
python -m scraper.run                      # 전체 실행
cd docs && python -m http.server 8000      # http://localhost:8000 에서 확인
python -m pytest -q tests                  # 중복 묶기 테스트
```

## 조절할 수 있는 값 (환경변수 또는 config.py)

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `TOP_N` | 8 | 분야별 카드 수 |
| `DEDUP_THRESHOLD` | 0.42 | 중복 판정 기준. 다른 뉴스가 묶이면 ↑, 같은 뉴스가 안 묶이면 ↓ |
| `LLM_MERGE` | 1 | AI로 같은 사건 2차 묶기 (0이면 끔) |
| `FETCH_BODY` | 1 | 기사 본문을 읽어 요약 품질 향상 (0이면 RSS 요약문만) |
| `CLAUDE_MODEL` | claude-haiku-5-5 | 품질을 더 원하면 `claude-sonnet-5-5` |
| `LOOKBACK_HOURS` | 24 | 몇 시간 이내 기사만 모을지 |

비용 감: 하루 카드 40장 기준 Haiku로 하루 수십 원~백 원대 수준입니다(본문 길이에 따라 달라짐).

## 글꼴

| 쓰임 | 글꼴 | 저작권·라이선스 |
|---|---|---|
| 로고·메뉴·제목·배지 | 서울알림체 (Bold, ExtraBold) | © 서울특별시 · 공공누리 제1유형(출처표시), 판매·유상양도 금지 |
| 본문·작은 글씨 | 프리젠테이션 (Regular, Medium, Bold) | © 이주임 · SIL OFL 1.1 |

`docs/fonts/` 에 웹폰트와 `FONTS-LICENSE.txt`(라이선스 전문)를 함께 넣어 두었고, 사이트 하단에 출처를 표시합니다(지우지 마세요).
서울알림체는 용량을 줄이려고 자주 쓰는 한글 2,350자와 영문·문장부호만 남겼어요. 드문 글자는 프리젠테이션으로 자연스럽게 대체됩니다.

## 저작권·운영 주의

- 사이트에는 **AI가 새로 쓴 요약과 원문 링크만** 올립니다. 기사 본문은 요약 입력으로만 쓰고 저장·게시하지 않아요.
- 언론사 RSS는 보통 개인·비상업 이용을 허용하지만, **광고 등 상업적으로 운영하려면** 각 언론사 이용약관을 확인하거나 제휴가 필요할 수 있습니다.
- RSS 주소는 언론사가 예고 없이 바꾸기도 합니다. 카드가 줄었다면 `--check-feeds` 로 확인하고 `config.py` 만 고치면 됩니다.
- AI 요약은 틀릴 수 있어 사이트 하단에 안내 문구와 원문 링크를 항상 함께 둡니다.

## 다음에 해볼 만한 것

- 카카오톡 알림 (비즈니스 채널·사업자 등록 필요)
- 퀴즈 연속 정답 기록, 주간 퀴즈 모아 풀기
- 키워드를 누르면 지난 날짜 카드까지 함께 모아보기
