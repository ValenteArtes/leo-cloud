import urllib.request
import json
import os

TELEGRAM_MASTER_TOKEN = "7571564726:AAFW5sQKdwfRlM8LRHNxDxqNZmuHj7glUQo"
MASTER_CHAT_ID = "7916905627"

def send_telemetry(action: str, details: str = ""):
    agent_name = os.environ.get("AGENT_NAME", "Léo")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_MASTER_TOKEN}/sendMessage"
        text = f"📡 [DASHBOARD S.A]\n🤖 Clone: {agent_name}\n📊 Evento: {action}\n📋 Detalhes: {details}"
        data = {
            "chat_id": MASTER_CHAT_ID,
            "text": text
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
