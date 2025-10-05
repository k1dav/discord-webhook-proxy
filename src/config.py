"""
Configuration management for Discord Webhook Proxy
Handles loading and saving YAML configuration files
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class Config:
    """Configuration manager for Discord Webhook Proxy"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f) or {}

        return self.data

    def save(self, data: Dict[str, Any]) -> None:
        """Save configuration to YAML file"""
        self.data = data
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

    def get_bot_token(self) -> Optional[str]:
        """Get bot token from configuration"""
        return self.data.get("bot", {}).get("token")

    def is_bot_enabled(self) -> bool:
        """Check if bot is enabled"""
        return self.data.get("bot", {}).get("enabled", True)

    def get_webhook_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """Get webhook rules from configuration"""
        rules = self.data.get("webhook_rules", [])

        if enabled_only:
            return [rule for rule in rules if rule.get("enabled", True)]

        return rules

    @staticmethod
    def create_example_config() -> Dict[str, Any]:
        """Create an example configuration"""
        return {
            "bot": {
                "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
                "enabled": True,
            },
            "webhook_rules": [
                {
                    "name": "全部訊息轉發",
                    "webhook_url": "https://discord.com/api/webhooks/...",
                    "enabled": True,
                    "event_type": None,  # None = all events
                    "scope_type": None,  # None = all scopes
                    "scope_id": None,
                },
                {
                    "name": "特定頻道訊息",
                    "webhook_url": "https://discord.com/api/webhooks/...",
                    "enabled": True,
                    "event_type": "message",
                    "scope_type": "channel",
                    "scope_id": "1234567890",
                },
            ],
        }
