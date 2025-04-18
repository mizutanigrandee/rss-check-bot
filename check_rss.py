import feedparser
import requests
import os
import json
import datetime
import pytz

# RSSフィードの設定（例）
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

# 検索キーワード（例）
KEYWORDS = ["京セラドーム", "京セラドーム大阪", "ヤンマースタジアム", "ヤンマースタジアム長居", "kyocera", "ドームツアー", "スタジアムツアー", "アジアツアー", "全国ツアー", "アリーナツアー", "ライブツアー", "ジャパンツアー", "ライブ情報解禁", "来日公演"]

# Slack Webhook URL（GitHub Secretsで設定済み）
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 通知済み記事の記録ファイル
FOUND_NEWS_FILE = "found_news.json"
# 夜間に取得した記事を一時保存するファイル
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
        return
    payload = {"text": text}
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"Slack送信失敗: {resp.text}")
    except Exception as e:
        print(f"Slack送信エラー: {e}")

if __name__ == "__main__":
    now = current_jst_time()
    # 日中: 7:00 <= time < 23:30
    daytime = now.hour >= 7 and (now.hour < 23 or (now.hour == 23 and now.minute < 30))
    # 夜間: 23:30 <= time or time < 7
    nighttime = not daytime

    found_news = load_json_file(FOUND_NEWS_FILE)
    night_notifications = load_json_file(NIGHT_NOTIFICATIONS_FILE)

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

            # 小文字に変換してキーワードチェック
            # ⇒ 全文（タイトル・要約・本文）を結合してチェックするよう変更
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].value
            full_text = "\n".join([title, summary, content]).lower()

            hit_keywords = [
                keyword for keyword in KEYWORDS
                if keyword.lower() in full_text
            ]

if hit_keywords:
    # 過去通知済みかチェック
    if link not in found_news:
        hit_keywords_str = "、".join(hit_keywords)
        msg = (
            f"【新ライブニュース】\n"
            f"タイトル: {title}\n"
            f"概要: {summary}\n"
            f"リンク: {link}\n"
            f"🔍ヒットキーワード: {hit_keywords_str}"
        )
        if daytime:
            # 日中は即時通知
            print("【日中通知】", msg)
            send_slack_message(msg)
        elif nighttime:
            # 夜間は保存しておく
            print("【夜間保存】", msg)
            night_notifications[link] = f"{title}（KW: {hit_keywords_str}）"
        # 記録に追加
        found_news[link] = title


    save_json_file(found_news, FOUND_NEWS_FILE)
    save_json_file(night_notifications, NIGHT_NOTIFICATIONS_FILE)

    # 朝7:00～7:15頃に、夜間に保存していた通知を一括送信する
    if now.hour == 7 and now.minute < 15 and night_notifications:
        batch_msg = "【朝一括通知】\n"
        for link, title in night_notifications.items():
            batch_msg += f"タイトル: {title}\nリンク: {link}\n\n"
        print("【朝通知】", batch_msg)
        send_slack_message(batch_msg)
        # 送信後、夜間保存データをクリア
        save_json_file({}, NIGHT_NOTIFICATIONS_FILE)
