"""아침 브리핑 알림 보내기 — 텔레그램 / 이메일 (설정한 것만 보냅니다)

필요한 환경변수 (GitHub Secrets에 넣기)
  공통      SITE_URL            사이트 주소 (예: https://아이디.github.io/shwipge/)
  텔레그램  TELEGRAM_BOT_TOKEN  @BotFather 에서 받은 봇 토큰
            TELEGRAM_CHAT_ID    받을 채팅/채널 id (채널이면 @채널이름 도 가능)
  이메일    SMTP_HOST, SMTP_PORT(기본 465), SMTP_USER, SMTP_PASSWORD, MAIL_TO(쉼표로 여러 명)
            지메일이면 SMTP_HOST=smtp.gmail.com, 비밀번호는 '앱 비밀번호'를 써야 해요.

사용법: python -m scraper.notify            # 보내기
        python -m scraper.notify --dry-run  # 내용만 출력
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import smtplib
import sys
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config

log = logging.getLogger("notify")


def load() -> dict:
    with open(os.path.join(config.OUTPUT_DIR, "news.json"), encoding="utf-8") as f:
        return json.load(f)


def card_url(site: str, card_id: str) -> str:
    return f"{site.rstrip('/')}/#card-{card_id}" if site else ""


def build_text(d: dict, site: str) -> str:
    names = {c["id"]: c["name"] for c in d["categories"]}
    lines = [f"☀️ 쉽게말해 · {d['date']} 아침 브리핑", ""]
    for i, b in enumerate(d.get("briefing", []), 1):
        lines.append(f"{i}. [{names.get(b['category'], '')}] {b['text']}")
    if d.get("quiz"):
        lines += ["", f"🧩 오늘의 퀴즈 {len(d['quiz'])}문제도 준비돼 있어요."]
    if site:
        lines += ["", f"👉 전체 보기: {site}"]
    return "\n".join(lines)


def build_html(d: dict, site: str) -> str:
    names = {c["id"]: c["name"] for c in d["categories"]}
    by_id = {c["id"]: c for c in d["cards"]}
    e = html.escape
    items = []
    for b in d.get("briefing", []):
        c = by_id.get(b["id"], {})
        link = card_url(site, b["id"])
        title = f'<a href="{e(link)}" style="color:#1d1c1a">{e(b["text"])}</a>' if link else e(b["text"])
        why = f'<div style="color:#b33c15;font-size:14px;margin-top:4px">나랑 무슨 상관? {e(c["why_me"])}</div>' if c.get("why_me") else ""
        items.append(
            f'<li style="margin:0 0 14px"><span style="color:#85817a;font-size:13px">{e(names.get(b["category"], ""))}</span><br>'
            f'<b style="font-size:16px">{title}</b>{why}</li>'
        )
    btn = (
        f'<p><a href="{e(site)}" style="display:inline-block;background:#e8572a;color:#fff;padding:10px 18px;'
        f'border-radius:10px;text-decoration:none;font-weight:700">오늘 뉴스 전체 보기</a></p>'
        if site else ""
    )
    return (
        '<div style="font-family:-apple-system,\'Apple SD Gothic Neo\',\'Malgun Gothic\',sans-serif;max-width:560px;'
        'line-height:1.6;color:#1d1c1a">'
        f'<h2 style="margin:0 0 4px">쉽게말해 아침 브리핑</h2><p style="color:#85817a;margin:0 0 18px">{e(d["date"])}</p>'
        f'<ol style="padding-left:20px">{"".join(items)}</ol>{btn}'
        '<p style="color:#85817a;font-size:12px">AI 요약이라 틀릴 수 있어요. 중요한 내용은 원문 기사를 확인하세요.</p></div>'
    )


def send_telegram(text: str) -> None:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        log.info("텔레그램 설정 없음 → 건너뜀")
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20) as r:
        r.read()
    log.info("텔레그램 전송 완료")


def send_email(subject: str, text: str, html_body: str) -> None:
    host, user, pw, to = (os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_TO"))
    if not (host and user and pw and to):
        log.info("이메일 설정 없음 → 건너뜀")
        return
    recipients = [x.strip() for x in to.split(",") if x.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(recipients)
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL(host, int(os.getenv("SMTP_PORT") or "465"), timeout=30) as s:
        s.login(user, pw)
        s.sendmail(user, recipients, msg.as_string())
    log.info("이메일 전송 완료 (%d명)", len(recipients))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    d = load()
    if d.get("sample"):
        log.info("예시 데이터라 알림을 보내지 않아요.")
        return 0
    site = os.getenv("SITE_URL", "")
    text = build_text(d, site)
    if args.dry_run:
        print(text)
        return 0

    failed = False
    for fn in (lambda: send_telegram(text), lambda: send_email(f"쉽게말해 · {d['date']} 아침 브리핑", text, build_html(d, site))):
        try:
            fn()
        except Exception as exc:  # 알림 실패가 사이트 업데이트를 망치지 않도록
            log.error("알림 실패: %s", exc)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
