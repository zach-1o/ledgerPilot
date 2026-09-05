import requests
import json
from typing import Dict, Any, Optional
from backend.config import load_settings

class TelegramChannel:
    """Telegram Bot Channel for real-time anomaly alerts and interactive inline approvals."""
    
    BASE_URL = "https://api.telegram.org/bot"

    @classmethod
    def get_api_url(cls, token: Optional[str] = None) -> str:
        settings = load_settings()
        bot_token = token or settings.telegram_bot_token
        return f"{cls.BASE_URL}{bot_token}"

    @classmethod
    def send_test_message(cls, token: str, chat_id: str) -> Dict[str, Any]:
        url = f"{cls.BASE_URL}{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🤖 *LedgerPilot Finance Controller*: Telegram Channel Connection Verified! You will receive real-time financial anomaly alerts and inline approval requests here.",
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def send_exception_alert(
        cls, 
        chain_id: str, 
        invoice_id: str, 
        discrepancy: float, 
        explanation: str, 
        severity: str = "HIGH",
        confidence: float = 0.94
    ) -> Optional[Dict[str, Any]]:
        settings = load_settings()
        token = settings.telegram_bot_token
        chat_id = settings.owner_chat_id

        if not token or not chat_id:
            print("Telegram Bot credentials not configured in settings. Skipping message.")
            return None

        text = (
            f"🔴 *LedgerPilot Anomaly Alert*\n\n"
            f"*Case ID*: `{chain_id}`\n"
            f"*Invoice*: `{invoice_id}`\n"
            f"*Financial Discrepancy*: `₹{discrepancy:,.2f}`\n"
            f"*Severity*: `{severity}`\n"
            f"*AI Confidence*: `{int(confidence * 100)}%`\n\n"
            f"📋 *Controller Diagnosis*:\n_{explanation}_\n\n"
            f"What would you like the AI Controller to do?"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve Adjustment", "callback_data": f"approve:{chain_id}"},
                    {"text": "❌ Escalate to Human", "callback_data": f"reject:{chain_id}"}
                ],
                [
                    {"text": "🔍 Inspect 4-Way Trace", "callback_data": f"inspect:{chain_id}"}
                ]
            ]
        }

        url = f"{cls.BASE_URL}{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}")
            return None
