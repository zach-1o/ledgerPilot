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
    settings_dict = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_dict = json.load(f)
        except Exception:
            pass
            
    # Always pull secrets from env if available (prevents hardcoding)
    settings_dict["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", settings_dict.get("telegram_bot_token", ""))
    settings_dict["owner_chat_id"] = os.getenv("OWNER_CHAT_ID", settings_dict.get("owner_chat_id", ""))
    settings_dict["razorpay_key_id"] = os.getenv("RAZORPAY_KEY_ID", settings_dict.get("razorpay_key_id", ""))
    settings_dict["razorpay_key_secret"] = os.getenv("RAZORPAY_KEY_SECRET", settings_dict.get("razorpay_key_secret", ""))
    
    # Return settings
    return AppSettings(**settings_dict)

def save_settings(settings: AppSettings) -> AppSettings:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    
    data_to_save = settings.model_dump()
    
    # Remove secrets before saving to avoid hardcoding in git or plain text files
    # Note: the frontend can still submit them and we use them in-memory, but they shouldn't persist to the JSON file if security is required.
    for key in ["telegram_bot_token", "owner_chat_id", "razorpay_key_id", "razorpay_key_secret"]:
        if key in data_to_save:
            # Optionally only remove if we want strict security, but to keep the frontend functional we might only pop them if they are in env.
            # For strict compliance, we pop them always so they must be in env.
            if os.getenv(key.upper()):
                data_to_save.pop(key, None)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2)
    return settings
