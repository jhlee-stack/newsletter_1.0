import feedparser
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import socket

socket.setdefaulttimeout(10)

GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECV_ADDRESS       = os.environ["RECV_ADDRESS"].split(",")

# ─── C2C 플랫폼 키워드 ────────────────────────────────
KEYWORDS = [
    "당근마켓", "당근", "번개장터", "중고나라",
    "C2C", "중고거래", "개인간거래", "리셀",
    "중고플랫폼", "버티컬커머스",
    "전금법", "전자금융거래법", "전자금융업", "선불충전금",
    "간편결제", "전자지급", "금융위원회"
]

# ─── 구글 뉴스 RSS ────────────────────────────────────
GOOGLE_NEWS_RSS = {
    "당근마켓":  "https://news.google.com/rss/search?q=당근마켓&hl=ko&gl=KR&ceid=KR:ko",
    "번개장터":  "https://news.google.com/rss/search?q=번개장터&hl=ko&gl=KR&ceid=KR:ko",
    "중고나라":  "https://news.google.com/rss/search?q=중고나라&hl=ko&gl=KR&ceid=KR:ko",
    "C2C동향":  "https://news.google.com/rss/search?q=C2C+커머스&hl=ko&gl=KR&ceid=KR:ko",
    "중고거래":  "https://news.google.com/rss/search?q=중고거래+플랫폼&hl=ko&gl=KR&ceid=KR:ko",
    "전금법":   "https://news.google.com/rss/search?q=전자금융거래법+개정&hl=ko&gl=KR&ceid=KR:ko",
    "선불충전금": "https://news.google.com/rss/search?q=선불충전금+규제&hl=ko&gl=KR&ceid=KR:ko",
}

FALLBACK_RSS     = "https://news.google.com/rss/search?q=중고거래+플랫폼&hl=ko&gl=KR&ceid=KR:ko"
MAX_PER_CATEGORY = 2
FALLBACK_COUNT   = 5


def fetch_news():
    results = {}
    seen = set()

    for cat, url in GOOGLE_NEWS_RSS.items():
        results[cat] = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if len(results[cat]) >= MAX_PER_CATEGORY:
                    break
                title   = entry.get("title", "").strip()
                link    = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                pub     = entry.get("published", "")
                if link in seen:
                    continue
                text = title + " " + summary
                if any(kw.lower() in text.lower() for kw in KEYWORDS):
                    results[cat].append({
                        "category": cat,
                        "title":    title,
                        "link":     link,
                        "summary":  summary[:150] + "..." if len(summary) > 150 else summary,
                        "pub":      pub,
                    })
                    seen.add(link)
            print(f"  [{cat}] {len(results[cat])}건 매칭")
        except Exception as e:
            print(f"  ❌ 오류 ({cat}): {e}")

    return results


def fetch_fallback():
    articles = []
    seen = set()
    try:
        feed = feedparser.parse(FALLBACK_RSS)
        for entry in feed.entries[:FALLBACK_COUNT]:
            link = entry.get("link", "").strip()
            if link in seen:
                continue
            articles.append({
                "category": "C2C 추천",
                "title":    entry.get("title", "").strip(),
                "link":     link,
                "summary":  entry.get("summary", "")[:150],
                "pub":      entry.get("published", ""),
            })
            seen.add(link)
        print(f"  대체 기사 {len(articles)}건 사용")
    except Exception as e:
        print(f"  ❌ 대체 기사 오류: {e}")
    return articles


def build_html(category_results, fallback_articles):
    now   = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    total = sum(len(v) for v in category_results.values())

    keyword_rows = ""
    for cat, articles in category_results.items():
        if articles:
            for i, art in enumerate(articles):
                bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
                keyword_rows += f"""
                <tr style="background:{bg}">
                  <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{art['category']}</td>
                  <td style="padding:6px 10px">
                    <a href="{art['link']}" style="color:#1a73e8;text-decoration:none;font-weight:bold">{art['title']}</a>
                    <div style="color:#555;font-size:12px;margin-top:3px">{art['summary']}</div>
                  </td>
                  <td style="padding:6px 10px;color:#aaa;font-size:11px;white-space:nowrap">{art['pub'][:16] if art['pub'] else ''}</td>
                </tr>"""
        else:
            keyword_rows += f"""
            <tr style="background:#fff8f0">
              <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{cat}</td>
              <td style="padding:6px 10px;color:#bbb;font-size:12px">0건 — 해당 키워드 기사 없음</td>
              <td></td>
            </tr>"""

    fallback_section = ""
    if fallback_articles:
        fallback_rows = ""
        for i, art in enumerate(fallback_articles):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            fallback_rows += f"""
            <tr style="background:{bg}">
              <td style="padding:6px 10px;color:#888;font-size:12px;white-space:nowrap">{art['category']}</td>
              <td style="padding:6px 10px">
                <a href="{art['link']}" style="color:#e8891a;text-decoration:none;font-weight:bold">{art['title']}</a>
                <div style="color:#555;font-size:12px;margin-top:3px">{art['summary']}</div>
              </td>
              <td style="padding:6px 10px;color:#aaa;font-size:11px;white-space:nowrap">{art['pub'][:16] if art['pub'] else ''}</td>
            </tr>"""
        fallback_section = f"""
        <div style="margin-top:24px">
          <div style="background:#e8891a;color:white;padding:12px 20px;border-radius:8px 8px 0 0">
            <h3 style="margin:0;font-size:15px">📌 오늘의 C2C 추천 뉴스</h3>
            <p style="margin:2px 0 0;font-size:12px;opacity:0.85">키워드 매칭 외 최신 기사</p>
          </div>
          <table width="100%" cellspacing="0" cellpadding="0"
                 style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
            <tbody>{fallback_rows}</tbody>
          </table>
        </div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;max-width:800px;margin:auto">
      <div style="background:#FF6F0F;color:white;padding:16px 20px;border-radius:8px 8px 0 0">
        <h2 style="margin:0">🛒 C2C 플랫폼 뉴스 알림</h2>
        <p style="margin:4px 0 0;font-size:13px;opacity:0.85">{now} 기준 · 당근마켓 · 번개장터 · 중고나라 · 총 {total}건</p>
      </div>
      <table width="100%" cellspacing="0" cellpadding="0"
             style="border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px">
        <thead><tr style="background:#f1f3f4">
          <th style="padding:8px 10px;text-align:left;font-size:12px">플랫폼</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">기사</th>
          <th style="padding:8px 10px;text-align:left;font-size:12px">시간</th>
        </tr></thead>
        <tbody>{keyword_rows}</tbody>
      </table>
      {fallback_section}
      <p style="color:#aaa;font-size:11px;text-align:center;margin-top:12px">
        GitHub Actions 뉴스봇
      </p>
    </body></html>"""


def send_email(category_results, fallback_articles):
    total   = sum(len(v) for v in category_results.values())
    now     = datetime.now().strftime("%m/%d %H:%M")
    subject = f"🛒 C2C 뉴스 알림 [{now}] {total}건"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"C2C 뉴스봇 <{GMAIL_ADDRESS}>"
    msg["To"]      = GMAIL_ADDRESS
    msg["Bcc"]     = ", ".join(RECV_ADDRESS)
    msg.attach(MIMEText(build_html(category_results, fallback_articles), "html", "utf-8"))

    all_recipients = [GMAIL_ADDRESS] + RECV_ADDRESS

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_ADDRESS, all_recipients, msg.as_string())
    print(f"✅ C2C 메일 전송 완료: {total}건")


if __name__ == "__main__":
    print(f"🔍 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] C2C 뉴스봇 시작")
    category_results  = fetch_news()
    fallback_articles = fetch_fallback()
    send_email(category_results, fallback_articles)
