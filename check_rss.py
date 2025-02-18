import feedparser
import requests
import os
import json

# 監視対象のRSSフィード（4つのサイト）
RSS_FEEDS = [
    "https://mdpr.jp/rss",
    "https://www.thefirsttimes.jp/feed/",
    "https://natalie.mu/music/feed/news",
    "https://www.billboard-japan.com/rss_data/music_news"
]

# 検索するキーワード
# 既存のキーワードに加え、「ヤンマースタジアム長居」と「京セラドーム大阪」を追加
KEYWORDS = [
    "京セラドーム", 
    "京セラドーム大阪", 
    "ヤンマースタジアム", 
    "ヤンマースタジアム長居", 
    "kyocera", 
    "osaka"
]

# SlackのWebhook URL（GitHub Secretsに設定）
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# 過去に通知したニュースを保存するファイル
FOUND_NEWS_FILE = "found_news.json"

def load_found_news():
    """
    過去に通知したニュースをロードする。
    ファイルが存在しないか破損している場合は、空の辞書を返す。
    形式: { "記事リンク": "記事タイトル", ... }
    """
    try:
        with open(FOUND_NEWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_found_news(data):
    """
    通知済みニュースをファイルに保存する。
    """
    with open(FOUND_NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_slack_message(text):
    """
    Slackにメッセージを送信する。
    """
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
    found_news = load_found_news()  # 過去の通知済みニュースを取得

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.title if hasattr(entry, "title") else ""
            # summary もしくは description を取得
            if hasattr(entry, "summary"):
                summary = entry.summary
            elif hasattr(entry, "description"):
                summary = entry.description
            else:
                summary = ""
            link = entry.link if hasattr(entry, "link") else ""

            # キーワードのチェックを、タイトルと本文の両方に対して小文字で実施
            title_lower = title.lower()
            summary_lower = summary.lower()
            if any(keyword.lower() in title_lower or keyword.lower() in summary_lower for keyword in KEYWORDS):
                # 既に通知済みの記事はスキップ
                if link not in found_news:
                    msg = f"【新ライブニュース】\nアーティスト情報は各メディアでご確認ください。\nタイトル: {title}\n概要: {summary}\nリンク: {link}"
                    print(msg)
                    send_slack_message(msg)
                    found_news[link] = title  # 通知済みリストに追加

    save_found_news(found_news)

