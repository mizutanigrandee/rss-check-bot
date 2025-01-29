import feedparser
import requests
import os
import json

# 🎯 監視対象のRSSフィード（4つのサイト）
RSS_FEEDS = [
    "https://mdpr.jp/rss",
    "https://www.thefirsttimes.jp/feed/",
    "https://natalie.mu/music/feed/news",
    "https://www.billboard-japan.com/rss_data/music_news"
]

# 🔍 検索するキーワード（ライブ発表関連）
KEYWORDS = ["京セラドーム", "ヤンマースタジアム", "kyocera"]

# 🚀 SlackのWebhook URL（GitHub Secretsに設定）
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 🔖 過去に通知したニュースを保存するファイル
FOUND_NEWS_FILE = "found_news.json"

def load_found_news():
    """過去の通知済みニュースをロード"""
    try:
        with open(FOUND_NEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_found_news(data):
    """通知済みニュースを保存"""
    with open(FOUND_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_slack_message(text):
    """Slackにメッセージを送信"""
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
    found_news = load_found_news()  # 過去の通知リストを取得

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            summary = entry.summary if "summary" in entry else ""  # 記事の要約があれば取得

            # キーワードを検索（タイトル or 本文）
            if any(keyword in title or keyword in summary for keyword in KEYWORDS):
                if link not in found_news:  # 過去の通知と重複チェック
                    msg = f"【新ライブニュース】\n{title}\n{summary}\n{link}"
                    print(msg)
                    send_slack_message(msg)
                    
                    found_news[link] = title  # 通知済みリストに追加

    save_found_news(found_news)  # 新しい記事リストを保存
