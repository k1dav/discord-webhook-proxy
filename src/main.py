"""
Discord Webhook Proxy - Config Editor
"""

import asyncio
import logging
from pathlib import Path

import discord
import streamlit as st
from config import Config
from listener_manager import ListenerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Config file path
CONFIG_FILE = "config.yaml"

# Event types supported by the bot
EVENT_TYPES = [
    "message",
    "member_join",
    "member_remove",
    "reaction_add",
    "channel_create",
    "channel_delete",
]

# Scope types
SCOPE_TYPES = [
    "全部範圍",
    "guild",
    "channel",
]


def init_app():
    """Initialize application components"""
    if "initialized" not in st.session_state:
        try:
            # Initialize config manager
            config_manager = Config(CONFIG_FILE)

            # Load config if exists, otherwise create default
            if Path(CONFIG_FILE).exists():
                config_manager.load()
                logger.info(f"Loaded configuration from {CONFIG_FILE}")
            else:
                # Create default config
                default_config = Config.create_example_config()
                config_manager.save(default_config)
                logger.info(f"Created default configuration at {CONFIG_FILE}")

            # Initialize listener manager
            listener_manager = ListenerManager()

            # Store in session state
            st.session_state.config = config_manager
            st.session_state.listener_manager = listener_manager
            st.session_state.initialized = True

            logger.info("Admin interface initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            st.error(f"初始化應用程式失敗: {e}")
            st.stop()


def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Discord Webhook Proxy",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize app first
    init_app()

    # Custom CSS for fonts and styling
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Section headers */
        .section-header {
            color: #e0e0e0;
            font-weight: 700;
            font-size: 1.5rem;
            margin: 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #3a3a3a;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Get components from session state
    config = st.session_state.get("config")
    listener_manager = st.session_state.get("listener_manager")

    # Sidebar navigation
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="margin: 0; font-size: 1.5rem; color: #e5e7eb; font-weight: 700;">
                Webhook Proxy Config
            </h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    # Initialize page in session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = "配置設定"

    pages = ["配置設定", "Listener 控制"]

    for page_name in pages:
        is_current = st.session_state.current_page == page_name

        if st.sidebar.button(
            page_name,
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if is_current else "secondary",
        ):
            st.session_state.current_page = page_name
            st.rerun()

    page = st.session_state.current_page

    # Main content
    if page == "配置設定":
        show_config_settings(config)
    elif page == "Listener 控制":
        show_listener_control(config, listener_manager)


def show_config_settings(config: Config):
    """Display config settings page - Bot settings and Webhook rules"""
    st.title("配置設定")
    st.markdown("配置 Discord Bot 和 Webhook 轉發規則")

    # Reload button
    if st.button("🔄 重新載入配置", use_container_width=False):
        try:
            config.load()
            st.success("✅ 配置已重新載入")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 重新載入失敗: {e}")

    st.markdown("---")

    # Bot Settings Section
    st.markdown("Bot 設定", unsafe_allow_html=True)

    # Get current bot config
    try:
        config.load()
        bot_config = config.data.get("bot", {})
    except Exception as e:
        st.error(f"載入配置失敗: {e}")
        return

    st.markdown(
        "從 [Discord Developer Portal](https://discord.com/developers/applications) 獲取你的 bot token"
    )

    with st.form("bot_config_form"):
        current_token = bot_config.get("token", "")
        token_display = (
            current_token[:10] + "..." + current_token[-10:]
            if current_token and len(current_token) > 20
            else current_token
        )

        if current_token:
            st.info(f"目前 Token: `{token_display}`")

        new_token = st.text_input(
            "Bot Token",
            type="password",
            placeholder="輸入新的 Discord Bot Token (留空表示不更改)",
            help="輸入你的 Discord bot token",
        )

        enabled = st.checkbox(
            "啟用 Bot",
            value=bot_config.get("enabled", True),
            help="停用後，discord_listener 將無法啟動",
        )

        save_button = st.form_submit_button(
            "儲存 Bot 設定", type="primary", use_container_width=True
        )

        if save_button:
            try:
                # Use new token if provided, otherwise keep existing
                token_to_save = new_token if new_token else current_token

                if not token_to_save:
                    st.error("❌ Token 不能為空")
                else:
                    # Update config.yaml
                    config.data["bot"] = {"token": token_to_save, "enabled": enabled}
                    config.save(config.data)
                    st.success("✅ Bot 設定已儲存到 config.yaml")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 儲存失敗: {e}")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Webhook Rules Section
    st.markdown(
        '<p class="section-header">Webhook 轉發規則</p>', unsafe_allow_html=True
    )

    # Check if we should switch to rules list tab after adding a rule
    if st.session_state.get("switch_to_rules_list", False):
        st.session_state.webhook_tab = "規則列表"
        st.session_state.switch_to_rules_list = False

    # Initialize webhook tab
    if "webhook_tab" not in st.session_state:
        st.session_state.webhook_tab = "規則列表"

    # Tab navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "📋 規則列表",
            use_container_width=True,
            type=(
                "primary" if st.session_state.webhook_tab == "規則列表" else "secondary"
            ),
            key="tab_rules_list",
        ):
            st.session_state.webhook_tab = "規則列表"
            st.rerun()

    with col2:
        if st.button(
            "➕ 新增規則",
            use_container_width=True,
            type=(
                "primary" if st.session_state.webhook_tab == "新增規則" else "secondary"
            ),
            key="tab_add_rule",
        ):
            st.session_state.webhook_tab = "新增規則"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Show selected tab content
    if st.session_state.webhook_tab == "規則列表":
        show_rules_list(config)
    else:
        show_add_rule(config)


def show_listener_control(config: Config, listener_manager: ListenerManager):
    """Display listener control page"""
    st.title("Listener 控制")
    st.markdown("控制 Discord Listener 的啟動、停止和重啟")

    st.markdown("---")

    # Get listener status
    listener_status = listener_manager.get_status()
    is_running = listener_status["is_running"]
    pid = listener_status.get("pid")

    # Status display
    status_color = "#10b981" if is_running else "#ef4444"
    status_text = "運行中" if is_running else "已停止"
    pid_text = f"PID: {pid}" if pid else ""

    st.markdown(
        f"""
        <div style="background: #1e1e1e; border: 1px solid {status_color}; border-left: 4px solid {status_color};
                    padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
            <p style="color: #9ca3af; margin: 0; font-size: 0.9rem; font-weight: 500;">Listener 狀態</p>
            <h1 style="color: #e5e7eb; margin: 0.5rem 0; font-size: 2.5rem; font-weight: 700;">
                <span style="color: {status_color};">●</span> {status_text}
            </h1>
            <p style="color: #9ca3af; margin: 0; font-size: 0.85rem;">{pid_text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Control buttons
    col1, col2, col3, col4 = st.columns(4)

    # Get bot config
    try:
        config.load()
        bot_config = config.data.get("bot", {})
    except:
        bot_config = {}

    with col1:
        if not is_running:
            if st.button("🚀 啟動 Listener", use_container_width=True, type="primary"):
                if not bot_config.get("token"):
                    st.error("❌ 請先設定 Bot Token")
                elif not bot_config.get("enabled", True):
                    st.error("❌ Bot 已停用，請先啟用 Bot")
                else:
                    try:
                        success = listener_manager.start()
                        if success:
                            st.success("✅ Discord Listener 已啟動")
                            st.rerun()
                        else:
                            st.error("❌ 啟動失敗，請查看日誌")
                    except Exception as e:
                        st.error(f"❌ 啟動失敗: {e}")
        else:
            st.button("🚀 啟動 Listener", use_container_width=True, disabled=True)

    with col2:
        if is_running:
            if st.button("⏹️ 停止 Listener", use_container_width=True):
                try:
                    success = listener_manager.stop()
                    if success:
                        st.success("✅ Discord Listener 已停止")
                        st.rerun()
                    else:
                        st.error("❌ 停止失敗")
                except Exception as e:
                    st.error(f"❌ 停止失敗: {e}")
        else:
            st.button("⏹️ 停止 Listener", use_container_width=True, disabled=True)

    with col3:
        if is_running:
            if st.button("🔄 重啟 Listener", use_container_width=True):
                try:
                    success = listener_manager.restart()
                    if success:
                        st.success("✅ Discord Listener 已重啟")
                        st.rerun()
                    else:
                        st.error("❌ 重啟失敗")
                except Exception as e:
                    st.error(f"❌ 重啟失敗: {e}")
        else:
            st.button("🔄 重啟 Listener", use_container_width=True, disabled=True)

    with col4:
        if st.button("🔄 重新整理", use_container_width=True):
            st.rerun()

    # Show logs
    if is_running:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<p class="section-header">📋 Listener 日誌</p>', unsafe_allow_html=True
        )
        with st.expander("查看最近日誌", expanded=False):
            logs = listener_manager.get_logs(lines=50)
            st.code(logs, language="log")


# ========== Discord Utils Functions ==========


async def fetch_bot_info(token: str):
    """Fetch bot information using temporary Discord client"""
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True

    client = discord.Client(intents=intents)
    bot_info = None

    @client.event
    async def on_ready():
        nonlocal bot_info
        logger.info(f"Temporary bot connected: {client.user}")

        try:
            bot_info = {
                "username": str(client.user),
                "user_id": client.user.id,
                "guilds_count": len(client.guilds),
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
                            if isinstance(channel, discord.TextChannel)
                        ],
                    }
                    for guild in client.guilds
                ],
            }
            logger.info(f"Fetched info for {len(client.guilds)} guilds")
        except Exception as e:
            logger.error(f"Error fetching bot info: {e}")
        finally:
            # Close the client after fetching info
            await client.close()

    try:
        # Start client with timeout
        await asyncio.wait_for(client.start(token), timeout=10.0)
    except asyncio.TimeoutError:
        logger.error("Timeout while connecting to Discord")
    except discord.LoginFailure:
        logger.error("Invalid bot token")
    except Exception as e:
        logger.error(f"Error connecting to Discord: {e}")
    finally:
        # Ensure client is closed and cleaned up
        if not client.is_closed():
            await client.close()

        # Wait a bit for cleanup
        await asyncio.sleep(0.5)

    return bot_info


def get_bot_info_sync(token: str):
    """Synchronous wrapper for fetch_bot_info"""
    try:
        try:
            asyncio.get_running_loop()
            # If we're already in an async context, run in a new thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(fetch_bot_info(token)))
                return future.result(timeout=15)
        except RuntimeError:
            # No event loop running, we can create one
            return asyncio.run(fetch_bot_info(token))
    except Exception as e:
        logger.error(f"Error in get_bot_info_sync: {e}")
        return None


# ========== Webhook Rules Functions ==========


def show_rules_list(config: Config):
    """Display list of webhook rules"""
    try:
        config.load()
        rules = config.get_webhook_rules()
    except Exception as e:
        st.error(f"載入規則列表失敗: {e}")
        return

    if not rules:
        st.info("尚未新增任何轉發規則")
        return

    for idx, rule in enumerate(rules):
        with st.container():
            col1, col2, col3 = st.columns([4, 2, 2])

            with col1:
                status_icon = "✅" if rule.get("enabled", True) else "❌"
                st.write(f"{status_icon} **{rule['name']}**")

                details = []
                event_type = rule.get("event_type")
                if event_type:
                    if isinstance(event_type, list):
                        events_str = ", ".join(event_type)
                    else:
                        events_str = str(event_type)
                    details.append(f"事件: {events_str}")
                else:
                    details.append("事件: 全部")

                scope_type = rule.get("scope_type")
                if scope_type:
                    scope_info = f"{scope_type}"
                    scope_id = rule.get("scope_id")
                    if scope_id:
                        scope_info += f" ({scope_id})"
                    details.append(f"範圍: {scope_info}")

                st.caption(" | ".join(details))

            with col2:
                webhook_short = (
                    rule["webhook_url"][:30] + "..."
                    if len(rule["webhook_url"]) > 30
                    else rule["webhook_url"]
                )
                st.caption(f"🌐 {webhook_short}")

            with col3:
                col_toggle, col_edit, col_delete = st.columns(3)

                with col_toggle:
                    if rule.get("enabled", True):
                        if st.button(
                            ":material/toggle_on:",
                            key=f"toggle_{idx}",
                            help="停用",
                        ):
                            toggle_rule(config, idx, False)
                    else:
                        if st.button(
                            ":material/toggle_off:",
                            key=f"toggle_{idx}",
                            help="啟用",
                        ):
                            toggle_rule(config, idx, True)

                with col_edit:
                    if st.button(":material/edit:", key=f"edit_btn_{idx}", help="編輯"):
                        st.session_state[f"edit_rule_{idx}"] = True

                with col_delete:
                    if st.button(
                        ":material/delete:",
                        key=f"delete_rule_{idx}",
                        help="刪除",
                    ):
                        delete_rule(config, idx)

            if st.session_state.get(f"close_edit_{idx}", False):
                st.session_state[f"edit_rule_{idx}"] = False
                st.session_state[f"close_edit_{idx}"] = False
                st.rerun()

            if st.session_state.get(f"edit_rule_{idx}", False):
                with st.expander("編輯規則", expanded=True):
                    show_edit_rule_form(config, idx, rule)

            st.divider()


def show_add_rule(config: Config):
    """Display add webhook rule form"""
    try:
        config.load()
        bot_token = config.get_bot_token()
    except:
        bot_token = None

    bot_info = None
    if bot_token:
        if "bot_info_cache" not in st.session_state or st.session_state.get(
            "refresh_bot_info"
        ):
            with st.spinner("正在連接 Discord 並獲取伺服器資訊..."):
                bot_info = get_bot_info_sync(bot_token)
                if bot_info:
                    st.session_state.bot_info_cache = bot_info
                    st.session_state.refresh_bot_info = False
        else:
            bot_info = st.session_state.bot_info_cache

    col1, col2 = st.columns([4, 1])
    with col1:
        if bot_info:
            st.info(f"✅ 已連接：{bot_info.get('guilds_count', 0)} 個伺服器")
        elif bot_token:
            st.warning("⚠️ 無法連接到 Discord")
        else:
            st.warning("⚠️ 請先設定 Bot Token")
    with col2:
        if bot_token:
            if st.button(
                "🔄 重新整理",
                key="refresh_bot_info_btn",
                help="重新從 Discord 獲取伺服器和頻道列表",
            ):
                st.session_state.refresh_bot_info = True
                st.rerun()

    st.markdown("---")

    st.write("**範圍設定**")
    scope_selection = st.selectbox("範圍類型", SCOPE_TYPES, key="add_scope_type")

    scope_id_value = None

    if scope_selection == "guild" and bot_info and bot_info.get("guilds"):
        guild_options = ["請選擇伺服器"] + [
            f"{guild['name']} (ID: {guild['id']})" for guild in bot_info["guilds"]
        ]
        guild_selection = st.selectbox(
            "選擇伺服器", guild_options, key="add_guild_select"
        )

        if guild_selection != "請選擇伺服器":
            try:
                scope_id_value = guild_selection.split("ID: ")[1].rstrip(")")
            except:
                st.error("無法解析伺服器 ID")

    elif scope_selection == "channel" and bot_info and bot_info.get("guilds"):
        guild_options = ["請選擇伺服器"] + [
            f"{guild['name']} (ID: {guild['id']})" for guild in bot_info["guilds"]
        ]
        guild_selection = st.selectbox(
            "選擇伺服器", guild_options, key="add_channel_guild_select"
        )

        if guild_selection != "請選擇伺服器":
            try:
                guild_id = guild_selection.split("ID: ")[1].rstrip(")")
                selected_guild = next(
                    (g for g in bot_info["guilds"] if str(g["id"]) == guild_id),
                    None,
                )

                if selected_guild and selected_guild.get("channels"):
                    channel_options = ["請選擇頻道"] + [
                        f"#{channel['name']} (ID: {channel['id']})"
                        for channel in selected_guild["channels"]
                    ]
                    channel_selection = st.selectbox(
                        "選擇頻道", channel_options, key="add_channel_select"
                    )

                    if channel_selection != "請選擇頻道":
                        try:
                            scope_id_value = channel_selection.split("ID: ")[1].rstrip(
                                ")"
                            )
                        except:
                            st.error("無法解析頻道 ID")
            except:
                pass

    elif scope_selection != "全部範圍":
        if not bot_token:
            st.warning("⚠️ 請先在「配置設定」頁面設定 Bot Token")
        elif not bot_info or not bot_info.get("guilds"):
            st.warning("⚠️ 無法連接到 Discord 或 Bot 未加入任何伺服器")

        scope_id_value = st.text_input(
            f"{scope_selection.title()} ID",
            placeholder=f"輸入 {scope_selection} 的 Discord ID",
            help="留空表示不限定特定 ID",
            key="add_scope_id_manual",
        )

    name = st.text_input(
        "規則名稱", placeholder="例如: 轉發所有訊息到 Discord", key="add_rule_name"
    )

    st.write("**事件類型**")
    st.caption("勾選要監聽的事件類型（不勾選代表全部事件）")

    event_checkboxes = {}
    cols = st.columns(3)
    for i, event in enumerate(EVENT_TYPES):
        with cols[i % 3]:
            event_checkboxes[event] = st.checkbox(event, key=f"add_event_{event}")

    with st.form("add_rule_form"):
        webhook_url = st.text_input(
            "Webhook URL",
            placeholder="https://discord.com/api/webhooks/...",
            help="Discord Webhook URL 或其他支援的 Webhook 端點",
        )

        enabled = st.checkbox("啟用規則", value=True)

        submitted = st.form_submit_button("新增規則")

        if submitted:
            if not name or not webhook_url:
                st.error("請填寫規則名稱和 Webhook URL")
            else:
                selected_events = [
                    event for event, checked in event_checkboxes.items() if checked
                ]
                event_type = selected_events if selected_events else None

                scope_type = None if scope_selection == "全部範圍" else scope_selection

                try:
                    new_rule = {
                        "name": name,
                        "webhook_url": webhook_url,
                        "enabled": enabled,
                        "event_type": event_type,
                        "scope_type": scope_type,
                        "scope_id": scope_id_value,
                    }

                    config.load()
                    if "webhook_rules" not in config.data:
                        config.data["webhook_rules"] = []
                    config.data["webhook_rules"].append(new_rule)
                    config.save(config.data)

                    # Switch to rules list tab after adding
                    st.session_state.switch_to_rules_list = True
                    st.success(f"✅ 規則 '{name}' 已成功新增！")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ 新增規則失敗: {e}")


def show_edit_rule_form(config: Config, idx: int, rule: dict):
    """Display edit webhook rule form"""
    st.info(f"**{rule['name']}** - {rule.get('scope_type') or '全部範圍'}")

    st.write("**調整事件類型**")
    st.caption("勾選要監聽的事件類型（不勾選代表全部事件）")

    current_events = []
    event_type = rule.get("event_type")
    if event_type:
        if isinstance(event_type, list):
            current_events = event_type
        else:
            current_events = [event_type]

    event_checkboxes = {}
    cols = st.columns(3)
    for i, event in enumerate(EVENT_TYPES):
        with cols[i % 3]:
            event_checkboxes[event] = st.checkbox(
                event,
                value=(event in current_events),
                key=f"edit_event_{idx}_{event}",
            )

    with st.form(f"edit_rule_form_{idx}"):
        col1, col2 = st.columns(2)
        with col1:
            save = st.form_submit_button("💾 儲存")
        with col2:
            cancel = st.form_submit_button("❌ 取消")

        if cancel:
            st.session_state[f"close_edit_{idx}"] = True
            st.rerun()

        if save:
            selected_events = [
                event for event, checked in event_checkboxes.items() if checked
            ]
            new_event_type = selected_events if selected_events else None

            try:
                config.load()
                config.data["webhook_rules"][idx]["event_type"] = new_event_type
                config.save(config.data)

                st.session_state[f"close_edit_{idx}"] = True
                st.success("✅ 事件類型已更新")

            except Exception as e:
                st.error(f"❌ 更新失敗: {e}")


def toggle_rule(config: Config, idx: int, enabled: bool):
    """Toggle webhook rule enabled status"""
    try:
        config.load()
        config.data["webhook_rules"][idx]["enabled"] = enabled
        config.save(config.data)
        status_text = "啟用" if enabled else "停用"
        st.success(f"✅ 規則已{status_text}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 更新失敗: {e}")


def delete_rule(config: Config, idx: int):
    """Delete a webhook rule"""
    try:
        config.load()
        del config.data["webhook_rules"][idx]
        config.save(config.data)
        st.success("✅ 規則已刪除")
        st.rerun()
    except Exception as e:
        st.error(f"❌ 刪除失敗: {e}")


if __name__ == "__main__":
    main()
