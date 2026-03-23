import urllib.request
import urllib.parse
import json
import os

TELEGRAM_MASTER_TOKEN = os.environ.get("TELEGRAM_MASTER_TOKEN", "")
MASTER_CHAT_ID = os.environ.get("MASTER_CHAT_ID", "")

def send_telemetry(action: str, details: str = ""):
    """Envia uma notificação silenciosa para o João Batista (Dashboard)"""
    if not TELEGRAM_MASTER_TOKEN or not MASTER_CHAT_ID:
        return
    
    agent_name = os.environ.get("AGENT_NAME", "Desconhecido")
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
