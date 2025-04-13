import requests
import os

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

response = requests.post(
    "https://slack.com/api/auth.test",
    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
)

print(response.json())
