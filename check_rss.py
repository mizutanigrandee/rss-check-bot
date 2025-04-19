import feedparser
import requests
import os
import json
import datetime
import pytz

# RSSフィードの設定
RSS_FEEDS = [
    "https://feed.mdpr.jp/rss/export/mdpr-topics.xml",
    "https://www.thefirsttimes.jp/feed/",
    "https://natalie.mu/music/feed/news",
    "https://news.yahoo.co.jp/rss/media/natalien/all.xml",
    "https://news.yahoo.co.jp/rss/media/mdpr/all.xml",
    "https://news.yahoo.co.jp/rss/media/exp/all.xml",
    "https://news.yahoo.co.jp/rss/media/oric/all.xml",
    "https://news.yahoo.co.jp/rss/media/kstylens/all.xml"
]

# 検索キーワード
KEYWORDS = [
    "京セラドーム", "京セラドーム大阪", "ヤンマースタジアム", "ヤンマースタジアム長居",
    "kyocera", "ドームツアー", "スタジアムツアー", "アジアツアー", "全国ツアー",
    "アリーナツアー", "ライブツアー", "ジャパンツアー", "ライブ情報解禁", "来日公演"
]

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
FOUND_NEWS_FILE = "found_news.json"
NIGHT_NOTIFICATIONS_FILE = "night_notifications.json"

def current_jst_time():
    return datetime.datetime.now(pytz.timezone("Asia/Tokyo"))

def load_json_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json_file(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_slack_message(text):
    if not SLACK_WEBHOOK_URL:
        print("Slack Webhook URL が設定されていません")
        return False
    payload = {"text": text}
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"Slack送信失敗: {resp.text}")
            return False
        return True
    except Exception as e:
        print(f"Slack送信エラー: {e}")
        return False

if __name__ == "__main__":
    now = current_jst_time()
    daytime = now.hour >= 7 and (now.hour < 23 or (now.hour == 23 and now.minute < 30))

    found_news = load_json_file(FOUND_NEWS_FILE)
    night_notifications = load_json_file(NIGHT_NOTIFICATIONS_FILE)

    if daytime and night_notifications:
        batch_msg = "【朝一括通知】\n"
        for link, title in night_notifications.items():
            batch_msg += f"タイトル: {title}\nリンク: {link}\n\n"
        print("【朝一括通知】", batch_msg)
        if send_slack_message(batch_msg):
            night_notifications.clear()

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.title if hasattr(entry, "title") else ""
            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description
            link = entry.link if hasattr(entry, "link") else ""

            title_lower = title.lower()
            summary_lower = summary.lower()

            hit_keywords = [
                kw for kw in KEYWORDS
                if kw.lower() in title_lower or kw.lower() in summary_lower
            ]

            if hit_keywords and link not in found_news:
                hit_keywords_str = "、".join(hit_keywords)
                msg = (
                    f"【新ライブニュース】\n"
                    f"タイトル: {title}\n"
                    f"概要: {summary}\n"
                    f"リンク: {link}\n"
                    f"🔍ヒットキーワード: {hit_keywords_str}"
                )
                if daytime:
                    if send_slack_message(msg):
                        found_news[link] = title
                else:
                    night_notifications[link] = f"{title}（KW: {hit_keywords_str}）"
                    found_news[link] = title

    save_json_file(found_news, FOUND_NEWS_FILE)
    save_json_file(night_notifications, NIGHT_NOTIFICATIONS_FILE)
