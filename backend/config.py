import json
import os
from pydantic import BaseModel, Field
from typing import Optional

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")

class AuthorityConfig(BaseModel):
    auto_approve_limit: float = 10000.0
    approval_required_limit: float = 50000.0

class AppSettings(BaseModel):
    telegram_bot_token: Optional[str] = ""
    owner_chat_id: Optional[str] = ""
    target_email: Optional[str] = "finance@merchant.com"
    authority: AuthorityConfig = Field(default_factory=AuthorityConfig)
    razorpay_key_id: Optional[str] = ""
    razorpay_key_secret: Optional[str] = ""
    enable_auto_sync: bool = False

def load_settings() -> AppSettings:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppSettings(**data)
        except Exception:
            pass
    
    # Return default settings if file doesn't exist
    defaults = AppSettings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        owner_chat_id=os.getenv("OWNER_CHAT_ID", ""),
        target_email=os.getenv("TARGET_EMAIL", "finance@merchant.com"),
        razorpay_key_id=os.getenv("RAZORPAY_KEY_ID", ""),
        razorpay_key_secret=os.getenv("RAZORPAY_KEY_SECRET", "")
    )
    save_settings(defaults)
    return defaults

def save_settings(settings: AppSettings) -> AppSettings:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2)
    return settings
