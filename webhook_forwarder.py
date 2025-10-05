"""
Webhook forwarder - handles event forwarding to webhooks based on rules
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class WebhookForwarder:
    """Forwards Discord events to webhooks based on YAML configuration"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize WebhookForwarder with YAML config

        Args:
            config: YAML configuration dict containing webhook rules
        """
        if not config:
            raise ValueError("Config must be provided")

        self.config = config
        self.session: Optional[httpx.Client] = None

    async def start(self):
        """Initialize the webhook forwarder"""
        # 使用同步 client
        timeout = httpx.Timeout(30.0, connect=10.0)
        self.session = httpx.Client(timeout=timeout)

    async def stop(self):
        """Close the webhook forwarder"""
        if self.session:
            self.session.close()

    async def handle_event(self, event_type: str, data: Dict[str, Any]):
        """Handle an event and forward to matching webhooks"""
        try:
            logger.debug(f"[WEBHOOK] Received event: type={event_type}")
            logger.info(f"Handling event: {event_type}, data: {data}")

            # Extract scope information from the event data
            scope_type = None
            scope_id = None

            # Determine scope based on event type and available data
            if "guild_id" in data and data["guild_id"]:
                scope_type = "guild"
                scope_id = str(data["guild_id"])
            elif "channel_id" in data:
                scope_type = "channel"
                scope_id = str(data["channel_id"])

            logger.debug(f"[WEBHOOK] Extracted scope: type={scope_type}, id={scope_id}")
            logger.info(f"Scope: type={scope_type}, id={scope_id}")

            # Get matching webhook rules from config
            rules = self._get_matching_rules_from_config(
                event_type=event_type,
                scope_type=scope_type,
                scope_id=scope_id,
            )

            logger.debug(f"[WEBHOOK] Found {len(rules)} matching rules")
            logger.info(f"Found {len(rules)} matching rules")

            if len(rules) == 0:
                logger.debug(
                    f"[WEBHOOK] No matching rules found for event_type={event_type}, scope_type={scope_type}, scope_id={scope_id}"
                )

            # Forward to each matching webhook (同步方式)
            for idx, rule in enumerate(rules):
                logger.debug(
                    f"[WEBHOOK] Processing rule {idx+1}/{len(rules)}: {rule['name']}"
                )
                logger.info(f"Forwarding to rule: {rule['name']}")
                self._forward_to_webhook_sync(
                    webhook_url=rule["webhook_url"],
                    rule_name=rule["name"],
                    event_type=event_type,
                    data=data,
                )

        except Exception as e:
            logger.error(f"Error handling event {event_type}: {e}")

    def _forward_to_webhook_sync(
        self, webhook_url: str, rule_name: str, event_type: str, data: Dict[str, Any]
    ):
        """Forward event data to a webhook URL (synchronous)"""
        if not self.session:
            logger.error("WebhookForwarder session not initialized")
            return

        try:
            # Prepare the payload - simple dict format
            payload = {
                "event_type": event_type,
                "rule_name": rule_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **data,  # Merge all event data directly into payload
            }

            logger.debug(
                f"[WEBHOOK] Sending to {webhook_url[:50]}... with payload keys: {list(payload.keys())}"
            )

            # Send to webhook
            logger.debug(f"[WEBHOOK] POSTing to webhook...")
            response = self.session.post(webhook_url, json=payload)
            logger.debug(f"[WEBHOOK] Received response: status={response.status_code}")

            if response.status_code in [200, 204]:
                logger.info(f"Successfully forwarded {event_type} to {rule_name}")
                logger.debug(f"[WEBHOOK] Success response body: {response.text[:200]}")
            else:
                logger.warning(
                    f"Webhook responded with status {response.status_code} for {rule_name}"
                )
                logger.debug(f"[WEBHOOK] Error response body: {response.text[:200]}")

        except Exception as e:
            logger.error(f"Error forwarding to webhook {rule_name}: {e}", exc_info=True)

    def _get_event_color(self, event_type: str) -> int:
        """Get color code for different event types"""
        colors = {
            "message": 0x3498DB,  # Blue
            "member_join": 0x2ECC71,  # Green
            "member_remove": 0xE74C3C,  # Red
            "reaction_add": 0xF39C12,  # Orange
            "channel_create": 0x9B59B6,  # Purple
            "channel_delete": 0xE67E22,  # Dark Orange
        }
        return colors.get(event_type, 0x95A5A6)  # Gray as default

    def _format_event_fields(self, data: Dict[str, Any]) -> list:
        """Format event data into Discord embed fields"""
        fields = []

        # Define display order and labels for known fields
        field_order = {
            "content": "Message",
            "author": "Author",
            "author_id": "Author ID",
            "member": "Member",
            "member_id": "Member ID",
            "user": "User",
            "user_id": "User ID",
            "channel": "Channel",
            "channel_id": "Channel ID",
            "is_thread": "Is Thread",
            "thread_name": "Thread",
            "thread_id": "Thread ID",
            "parent_channel_id": "Parent Channel ID",
            "guild": "Guild",
            "guild_id": "Guild ID",
            "emoji": "Emoji",
            "message_id": "Message ID",
            "joined_at": "Joined At",
            "timestamp": "Time",
        }

        # Add fields in specified order
        for key, label in field_order.items():
            if key in data and data[key] is not None:
                value = str(data[key])
                # Truncate long values
                if len(value) > 1024:
                    value = value[:1021] + "..."

                fields.append({"name": label, "value": value, "inline": True})

        # Add any remaining fields not in the order list
        for key, value in data.items():
            if key not in field_order and value is not None:
                display_value = str(value)
                # Truncate long values
                if len(display_value) > 1024:
                    display_value = display_value[:1021] + "..."

                fields.append(
                    {
                        "name": key.replace("_", " ").title(),
                        "value": display_value,
                        "inline": True,
                    }
                )

        return (
            fields
            if fields
            else [
                {"name": "Event Data", "value": "No additional data", "inline": False}
            ]
        )

    def test_webhook_sync(self, webhook_url: str) -> bool:
        """Test if a webhook URL is valid"""
        try:
            payload = {
                "content": "Test message from Discord Webhook Proxy",
                "embeds": [
                    {
                        "title": "Webhook Test",
                        "description": "This is a test message to verify the webhook is working correctly.",
                        "color": 0x00FF00,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            }

            # 使用臨時同步 client 避免與主 session 衝突
            timeout = httpx.Timeout(10.0, connect=5.0)
            with httpx.Client(timeout=timeout) as client:
                response = client.post(webhook_url, json=payload)
                return response.status_code == 204

        except Exception as e:
            logger.error(f"Error testing webhook: {e}")
            return False

    def _get_matching_rules_from_config(
        self,
        event_type: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get webhook rules matching the event criteria from YAML config"""
        if not self.config:
            return []

        rules = self.config.get("webhook_rules", [])
        matching_rules = []

        for rule in rules:
            # Skip disabled rules
            if not rule.get("enabled", True):
                continue

            # Check event type match
            rule_event_type = rule.get("event_type")
            if rule_event_type is None:
                # None means all events
                event_match = True
            else:
                # Check if it's a list or single value
                if isinstance(rule_event_type, list):
                    event_match = event_type in rule_event_type
                elif isinstance(rule_event_type, str):
                    # Try to parse as JSON first
                    try:
                        event_types = json.loads(rule_event_type)
                        if isinstance(event_types, list):
                            event_match = event_type in event_types
                        else:
                            event_match = rule_event_type == event_type
                    except:
                        event_match = rule_event_type == event_type
                else:
                    event_match = False

            # Check scope match
            scope_match = True
            rule_scope_type = rule.get("scope_type")
            rule_scope_id = rule.get("scope_id")

            if scope_type and scope_id and rule_scope_type is not None:
                scope_match = rule_scope_type == scope_type and str(
                    rule_scope_id
                ) == str(scope_id)

            if event_match and scope_match:
                matching_rules.append(rule)

        return matching_rules
