import os
from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_API_URL = "https://slack.com/api/chat.postMessage"

app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Slackのリトライ対策
    if request.headers.get("X-Slack-Retry-Num"):
        return "No retry", 200

    data = request.get_json()

    # URL検証イベント
    if data.get("type") == "url_verification":
        return data.get("challenge")

    if "event" in data:
        event = data["event"]

        # bot自身のメッセージには反応しない
        if event.get("type") in ["app_mention", "message"]:
            if event.get("subtype") == "bot_message":
                return "Ignore bot message", 200
            
            if event.get("user") == os.environ.get("BOT_USER_ID"):
                return "Ignore own message", 200

            text = event.get("text", "")
            channel = event.get("channel")
            thread_ts = event.get("ts")

            try:
                # !vote を含むか確認
                if "!vote" not in text:
                    return "No vote trigger", 200

                # "!vote 選択肢1, 選択肢2, ..." を分解
                parts = text.split("!vote", 1)[1].strip()
                options = [opt.strip() for opt in parts.split(",") if opt.strip()]

                headers = {
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                }

                # ❌ 選択肢が0個
                if len(options) == 0:
                    error_message = "⚠️ 投票の選択肢が見つかりませんでした。'!vote 選択肢1, 選択肢2, ...' の形式で入力してください"
                    error_payload = {
                        "channel": channel,
                        "text": error_message,
                        "thread_ts": thread_ts
                    }
                    requests.post(SLACK_API_URL, json=error_payload, headers=headers)
                    return "Zero option", 200

                # ❌ 選択肢が11個以上
                if len(options) > 10:
                    error_message = f"⚠️ 投票の選択肢が多すぎます（最大10個まで）。現在: {len(options)}個"
                    error_payload = {
                        "channel": channel,
                        "text": error_message,
                        "thread_ts": thread_ts
                    }
                    requests.post(SLACK_API_URL, json=error_payload, headers=headers)
                    return "Too many options", 200

                if 0 < len(options) < 11:
                    # ✅ 投票メッセージ作成
                    emojis = [":one:", ":two:", ":three:", ":four:", ":five:",
                            ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:"]

                    message = "📊 投票してください！\n"
                    for i, option in enumerate(options):
                        message += f"{emojis[i]} {option}\n"

                    payload = {
                        "channel": channel,
                        "text": message
                    }

                    res = requests.post(SLACK_API_URL, json=payload, headers=headers)
                    msg_ts = res.json().get("ts")

                    # ✅ 投票用リアクション追加
                    for i in range(len(options)):
                        reaction_payload = {
                            "channel": channel,
                            "name": emojis[i].strip(":"),
                            "timestamp": msg_ts
                        }
                        requests.post("https://slack.com/api/reactions.add", headers=headers, json=reaction_payload)

            except Exception as e:
                error_message = f"⚠️ 投票の形式に問題があります: {str(e)}"
                error_payload = {
                    "channel": channel,
                    "text": error_message,
                    "thread_ts": thread_ts
                }
                requests.post(SLACK_API_URL, json=error_payload, headers=headers)

    return "OK"

if __name__ == "__main__":
    app.run(port=3000)
