"""Discord bot manager - handles single bot instance."""

import asyncio
import logging
from typing import Callable, Optional

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class BotManager:
    """Manages a single Discord bot instance and its lifecycle."""

    def __init__(self, token: Optional[str] = None) -> None:
        """初始化 bot 管理器。

        Args:
            token: Discord bot token (可選)
        """
        self.token = token
        self.bot: Optional[commands.Bot] = None
        self.event_handler: Optional[Callable] = None
        self._is_running = False

    def set_token(self, token: str) -> None:
        """設定 bot token。

        Args:
            token: Discord bot token
        """
        self.token = token

    def set_event_handler(self, handler: Callable) -> None:
        """設定事件處理器回調函數。

        Args:
            handler: 處理 bot 事件的非同步可調用對象
        """
        self.event_handler = handler

    def _create_bot_instance(self) -> commands.Bot:
        """建立一個擁有所有 intents 的新 Discord bot 實例。

        Returns:
            已配置的 Discord bot 實例
        """
        intents = discord.Intents.all()
        bot = commands.Bot(command_prefix="!", intents=intents)
        return bot

    def _register_event_handlers(self, bot: commands.Bot) -> None:
        """為 bot 實例註冊所有事件處理器。

        Args:
            bot: Discord bot 實例
        """

        @bot.event
        async def on_ready() -> None:
            """處理 bot 就緒事件。"""
            logger.info(f"Bot {bot.user} 已就緒並連接")
            self._is_running = True

        @bot.event
        async def on_message(message: discord.Message) -> None:
            """處理接收到的訊息。"""
            # Debug: Log all messages received
            logger.debug(
                f"[MESSAGE] Received from {message.author} (bot={message.author.bot}): {message.content[:50]}..."
            )

            if self.event_handler and not message.author.bot:
                try:
                    message_data = self._build_message_data(message)
                    logger.debug(
                        f"[MESSAGE] Building message data for guild_id={message.guild.id if message.guild else None}, channel_id={message.channel.id}"
                    )
                    logger.info(f"Message event data: {message_data}")

                    # Debug: Log before calling handler
                    logger.debug(
                        f"[MESSAGE] Calling event handler with event_type='message'"
                    )
                    await self.event_handler(
                        event_type="message",
                        data=message_data,
                    )
                    logger.debug(f"[MESSAGE] Event handler completed successfully")
                except Exception as e:
                    logger.error(f"處理訊息事件時發生錯誤: {e}", exc_info=True)

        @bot.event
        async def on_member_join(member: discord.Member) -> None:
            """處理成員加入事件。"""
            if self.event_handler:
                try:
                    await self.event_handler(
                        event_type="member_join",
                        data=self._build_member_data(member, include_joined_at=True),
                    )
                except Exception as e:
                    logger.error(f"處理成員加入事件時發生錯誤: {e}")

        @bot.event
        async def on_member_remove(member: discord.Member) -> None:
            """處理成員移除事件。"""
            if self.event_handler:
                try:
                    await self.event_handler(
                        event_type="member_remove",
                        data=self._build_member_data(member),
                    )
                except Exception as e:
                    logger.error(f"處理成員移除事件時發生錯誤: {e}")

        @bot.event
        async def on_reaction_add(
            reaction: discord.Reaction, user: discord.User
        ) -> None:
            """處理新增反應事件。"""
            if self.event_handler and not user.bot:
                try:
                    await self.event_handler(
                        event_type="reaction_add",
                        data=self._build_reaction_data(reaction, user),
                    )
                except Exception as e:
                    logger.error(f"處理反應事件時發生錯誤: {e}")

        @bot.event
        async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
            """處理頻道建立事件。"""
            if self.event_handler:
                try:
                    await self.event_handler(
                        event_type="channel_create",
                        data=self._build_channel_data(channel),
                    )
                except Exception as e:
                    logger.error(f"處理頻道建立事件時發生錯誤: {e}")

        @bot.event
        async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
            """處理頻道刪除事件。"""
            if self.event_handler:
                try:
                    await self.event_handler(
                        event_type="channel_delete",
                        data=self._build_channel_data(channel),
                    )
                except Exception as e:
                    logger.error(f"處理頻道刪除事件時發生錯誤: {e}")

    @staticmethod
    def _build_message_data(message: discord.Message) -> dict:
        """建立訊息的事件資料字典。

        Args:
            message: Discord 訊息物件

        Returns:
            包含訊息事件資料的字典
        """
        # Check if message is in a thread
        is_thread = isinstance(message.channel, discord.Thread)

        return {
            "content": message.content,
            "author": str(message.author),
            "author_id": message.author.id,
            "channel": str(message.channel),
            "channel_id": message.channel.id,
            "guild": str(message.guild) if message.guild else None,
            "guild_id": message.guild.id if message.guild else None,
            "timestamp": message.created_at.isoformat(),
            "is_thread": is_thread,
            "thread_id": message.channel.id if is_thread else None,
            "thread_name": message.channel.name if is_thread else None,
            "parent_channel": str(message.channel.parent) if is_thread and message.channel.parent else None,
            "parent_channel_id": message.channel.parent_id if is_thread else None,
        }

    @staticmethod
    def _build_member_data(
        member: discord.Member, include_joined_at: bool = False
    ) -> dict:
        """建立成員的事件資料字典。

        Args:
            member: Discord 成員物件
            include_joined_at: 是否包含加入時間戳記

        Returns:
            包含成員事件資料的字典
        """
        data = {
            "member": str(member),
            "member_id": member.id,
            "guild": str(member.guild),
            "guild_id": member.guild.id,
        }

        if include_joined_at:
            data["joined_at"] = (
                member.joined_at.isoformat() if member.joined_at else None
            )

        return data

    @staticmethod
    def _build_reaction_data(reaction: discord.Reaction, user: discord.User) -> dict:
        """建立反應的事件資料字典。

        Args:
            reaction: Discord 反應物件
            user: 新增反應的使用者

        Returns:
            包含反應事件資料的字典
        """
        return {
            "emoji": str(reaction.emoji),
            "user": str(user),
            "user_id": user.id,
            "message_id": reaction.message.id,
            "channel": str(reaction.message.channel),
            "channel_id": reaction.message.channel.id,
            "guild": str(reaction.message.guild) if reaction.message.guild else None,
            "guild_id": reaction.message.guild.id if reaction.message.guild else None,
        }

    @staticmethod
    def _build_channel_data(channel: discord.abc.GuildChannel) -> dict:
        """建立頻道的事件資料字典。

        Args:
            channel: Discord 頻道物件

        Returns:
            包含頻道事件資料的字典
        """
        return {
            "channel": str(channel),
            "channel_id": channel.id,
            "guild": str(channel.guild),
            "guild_id": channel.guild.id,
        }

    def start(self) -> None:
        """在背景執行緒中啟動 bot 實例。"""
        if self._is_running or self.bot:
            logger.warning("Bot 已在執行中")
            return

        if not self.token:
            raise ValueError("Bot token 未設定。請先設定 token。")

        import threading

        def run_bot_thread():
            """在新的事件循環中執行 bot。"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.bot = self._create_bot_instance()
            self._register_event_handlers(self.bot)

            try:
                loop.run_until_complete(self.bot.start(self.token))
            except Exception as e:
                if "Connector is closed" not in str(e):
                    logger.error(f"執行 bot 時發生錯誤: {e}")
            finally:
                loop.run_until_complete(self.bot.close())
                loop.close()
                self._is_running = False
                self.bot = None

        thread = threading.Thread(target=run_bot_thread, daemon=True)
        thread.start()
        self._is_running = True
        logger.info("Bot 已在背景啟動...")

    def stop(self) -> None:
        """停止 bot 實例。"""
        if not self.bot:
            logger.warning("Bot 未在執行中")
            return

        # 關閉 bot 連接
        try:
            if not self.bot.is_closed():
                # 在 bot 自己的事件循環中關閉
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._close_bot_sync)
                    future.result(timeout=5)
        except Exception as e:
            logger.debug(f"關閉 bot 時的錯誤（可忽略）: {e}")

        self.bot = None
        self._is_running = False
        logger.info("Bot 已停止")

    def _close_bot_sync(self):
        """同步關閉 bot（在 bot 的執行緒中執行）。"""
        if self.bot and not self.bot.is_closed():
            loop = self.bot.loop
            if loop and not loop.is_closed():
                asyncio.run_coroutine_threadsafe(self.bot.close(), loop).result(
                    timeout=5
                )

    def restart(self) -> None:
        """重啟 bot 實例。"""
        self.stop()
        import time

        time.sleep(1)  # 允許清理完成
        self.start()

    def is_running(self) -> bool:
        """檢查 bot 是否正在執行。

        Returns:
            如果 bot 正在執行則返回 True，否則返回 False
        """
        return self.bot is not None and not self.bot.is_closed()

    def is_ready(self) -> bool:
        """檢查 bot 是否已就緒。

        Returns:
            如果 bot 已就緒則返回 True，否則返回 False
        """
        return self.bot is not None and self.bot.is_ready()

    def get_bot_info(self) -> Optional[dict]:
        """取得 bot 資訊。

        Returns:
            包含 bot 資訊的字典，如果 bot 未執行則返回 None
        """
        if not self.bot or not self.bot.user:
            return None

        return {
            "username": str(self.bot.user),
            "user_id": self.bot.user.id,
            "is_ready": self.bot.is_ready(),
            "guilds_count": len(self.bot.guilds),
            "guilds": [
                {
                    "id": guild.id,
                    "name": guild.name,
                    "member_count": guild.member_count,
                    "channels": [
                        {
                            "id": channel.id,
                            "name": channel.name,
                            "type": str(channel.type),
                        }
                        for channel in guild.channels
                    ],
                }
                for guild in self.bot.guilds
            ],
        }
