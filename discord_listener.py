"""
Discord Event Listener - Standalone Script

This script runs independently to listen to Discord events and forward them
to configured webhooks based on YAML configuration.
"""

import asyncio
import logging
import signal
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bot_manager import BotManager
from src.config import Config
from webhook_forwarder import WebhookForwarder

# Configure logging with rotation
# Max file size: 10MB, keep 5 backup files
log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Rotating file handler (10MB max, 5 backups)
file_handler = RotatingFileHandler(
    "discord_listener.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(log_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Configure root logger (set to DEBUG to see detailed message logs)
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)


class DiscordListener:
    """Main Discord listener service"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.bot_manager: BotManager = None
        self.webhook_forwarder: WebhookForwarder = None
        self.running = False

    async def initialize(self):
        """Initialize components from YAML configuration"""
        logger.info("Initializing Discord listener...")

        # Load configuration from YAML file
        logger.info(f"Loading configuration from: {self.config_path}")
        config_manager = Config(self.config_path)
        config_data = config_manager.load()

        # Validate bot configuration
        bot_token = config_manager.get_bot_token()
        if not bot_token:
            logger.error("No bot token found in configuration file.")
            raise ValueError("Bot token not configured")

        if not config_manager.is_bot_enabled():
            logger.warning("Bot is disabled in configuration")
            raise ValueError("Bot is disabled")

        # Initialize bot manager
        self.bot_manager = BotManager(bot_token)
        logger.info("Bot manager initialized")

        # Initialize webhook forwarder with YAML config
        self.webhook_forwarder = WebhookForwarder(config=config_data)
        await self.webhook_forwarder.start()
        logger.info("Webhook forwarder started")

        # Set event handler
        self.bot_manager.set_event_handler(self.webhook_forwarder.handle_event)
        logger.info("Event handler configured")

    async def start(self):
        """Start the Discord listener"""
        try:
            await self.initialize()

            logger.info("Starting Discord bot...")
            self.bot_manager.start()
            self.running = True

            logger.info("Discord listener is now running. Press Ctrl+C to stop.")

            # Keep the script running
            while self.running:
                await asyncio.sleep(1)

                # Check if bot is still running
                if not self.bot_manager.is_running():
                    logger.warning("Bot stopped unexpectedly, attempting restart...")
                    try:
                        self.bot_manager.restart()
                    except Exception as e:
                        logger.error(f"Failed to restart bot: {e}")
                        self.running = False
                        break

        except Exception as e:
            logger.error(f"Error starting Discord listener: {e}")
            raise

    async def stop(self):
        """Stop the Discord listener"""
        logger.info("Stopping Discord listener...")
        self.running = False

        if self.bot_manager:
            self.bot_manager.stop()
            logger.info("Bot stopped")

        if self.webhook_forwarder:
            await self.webhook_forwarder.stop()
            logger.info("Webhook forwarder stopped")

        logger.info("Discord listener stopped successfully")


def signal_handler(signum, _frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Default config file
    config_file = "config.yaml"

    # Check if config file exists
    if not Path(config_file).exists():
        logger.error(f"Configuration file not found: {config_file}")
        logger.error(
            "Please create config.yaml or use Streamlit admin interface to generate it"
        )
        sys.exit(1)

    logger.info(f"Using configuration file: {config_file}")
    listener = DiscordListener(config_path=config_file)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await listener.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        await listener.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
