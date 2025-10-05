# 🤖 Discord Webhook Proxy

一個現代化的 Discord 事件監聽與 Webhook 轉發系統，採用分離式架構設計。

## ✨ 功能特色

- 🎯 **獨立 Discord 監聽器** - 獨立的 Discord bot 服務，持續監聽事件
- 🎛️ **Streamlit 管理介面** - 易用的網頁管理界面，管理 bot 設定和 webhook 規則
- 📊 **彈性規則系統** - 支援多種事件類型和作用域過濾
- 🔄 **即時轉發** - 自動將 Discord 事件轉發到配置的 Webhook
- 💾 **YAML 配置** - 純 YAML 檔案配置，易於版本控制和部署
- 📝 **視覺化管理** - Streamlit 介面直接編輯 YAML 配置

## 🏗️ 架構設計

本專案採用分離式架構：

```
┌─────────────────────┐       ┌──────────────────┐
│  Discord Listener   │       │  Streamlit Admin │
│  (discord_listener) │       │     (main.py)    │
│                     │       │                  │
│  - 監聽 Discord 事件 │       │  - 管理 Bot 設定  │
│  - 轉發到 Webhooks   │       │  - 管理 Webhook 規則 │
│  - 獨立運行         │       │  - 視覺化編輯介面 │
└──────────┬──────────┘       └────────┬─────────┘
           │                           │
           │      ┌────────────┐      │
           └──────►  config.yaml ◄─────┘
                  │ YAML 配置檔 │
                  └────────────┘
```

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 使用 UV (推薦)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 啟動管理介面

```bash
uv run streamlit run src/main.py
```

### 3. 配置 Bot Token

在管理介面中：
1. 前往「Bot 設定」頁面
2. 輸入你的 Discord Bot Token
3. 勾選「啟用 Bot」
4. 點擊「儲存設定」

### 4. 設定 Webhook 規則

1. 在管理介面前往「Webhook 規則」頁面
2. 點擊「新增規則」標籤
3. 填寫規則資訊：
   - 規則名稱
   - 事件類型（如：message, member_join 等）
   - 作用域（guild, channel 或全部）
   - Webhook URL
4. 點擊「新增規則」

### 5. 啟動 Discord 監聽器

Discord Listener 會自動讀取 `config.yaml` 配置檔案。

**方式 1：從 Streamlit 介面啟動（推薦）**

1. 在「Bot 設定」或「儀表板」頁面
2. 點擊「🚀 啟動 Listener」按鈕
3. 監聽器將在背景運行並讀取 `config.yaml`

**方式 2：手動啟動**

```bash
python discord_listener.py
```

注意：程式會自動讀取 `config.yaml`，請確保該檔案存在

### 6. 管理 Listener

在 Streamlit 介面中，你可以：
- ✅ 查看 Listener 運行狀態
- 🚀 啟動 Listener
- ⏹️ 停止 Listener
- 🔄 重啟 Listener
- 📋 查看即時日誌

## 📁 專案結構

```
discord-webhook-proxy/
├── src/                        # 源碼目錄
│   ├── main.py                # Streamlit 管理介面
│   ├── config.py              # YAML 配置管理
│   ├── bot_manager.py         # Discord Bot 管理
│   ├── webhook_forwarder.py   # Webhook 轉發邏輯
│   ├── listener_manager.py    # Listener 進程管理
│   ├── utils.py               # 工具函數
│   └── views/                 # Streamlit 視圖
│       └── webhook_rules.py   # Webhook 規則管理頁面
├── discord_listener.py         # 獨立的 Discord 監聽器服務
├── config.example.yaml        # YAML 配置範例
├── config.yaml                # YAML 配置檔案 (自動生成)
├── pyproject.toml             # 專案配置
└── README.md                  # 專案說明
```

## 🔧 支援的事件類型

- `message` - 訊息事件
- `member_join` - 成員加入
- `member_remove` - 成員離開
- `reaction_add` - 反應新增
- `channel_create` - 頻道建立
- `channel_delete` - 頻道刪除

## 🎯 使用範例

### 範例 1：轉發所有訊息到 Discord Webhook

1. 新增規則：
   - 名稱：`轉發所有訊息`
   - 事件類型：勾選 `message`
   - 作用域：`全部範圍`
   - Webhook URL：你的 Discord Webhook URL

### 範例 2：監控特定頻道的成員加入事件

1. 新增規則：
   - 名稱：`監控新成員`
   - 事件類型：勾選 `member_join`
   - 作用域：`channel`
   - Channel ID：你的頻道 ID
   - Webhook URL：你的 Discord Webhook URL

## 📝 YAML 配置說明

### 配置檔案格式

使用 YAML 配置檔案可以更方便地管理和部署配置。配置檔案包含兩個主要部分：

1. **Bot 設定** - Discord Bot Token 和啟用狀態
2. **Webhook 規則** - 事件轉發規則列表

### 配置範例

請參考 `config.example.yaml` 檔案，以下是基本結構：

```yaml
bot:
  token: "YOUR_DISCORD_BOT_TOKEN_HERE"
  enabled: true

webhook_rules:
  - name: "全部訊息轉發"
    webhook_url: "https://discord.com/api/webhooks/..."
    enabled: true
    event_type: null  # null = 所有事件
    scope_type: null  # null = 所有範圍
    scope_id: null
```

### 事件類型設定

- `event_type: null` - 接收所有事件
- `event_type: "message"` - 只接收訊息事件
- `event_type: ["message", "member_join"]` - 接收多種事件類型

### 範圍設定

- `scope_type: null` - 所有範圍
- `scope_type: "guild"` + `scope_id: "123"` - 特定伺服器
- `scope_type: "channel"` + `scope_id: "456"` - 特定頻道

### 使用 YAML 配置的優勢

- ✅ 版本控制友好（可移除敏感資料後提交）
- ✅ 便於批量配置和部署
- ✅ 可在 Streamlit 介面中配置後導出
- ✅ 支援快速切換不同配置環境

## 🐳 Docker 部署

### 方式 1：分別運行服務

```bash
# 終端機 1 - 運行管理介面
docker run -p 8501:8501 -v $(pwd)/config.yaml:/app/config.yaml discord-webhook-proxy streamlit run src/main.py

# 終端機 2 - 運行監聽器
docker run -v $(pwd)/config.yaml:/app/config.yaml discord-webhook-proxy python discord_listener.py
```

### 方式 2：使用 Docker Compose (推薦)

創建 `docker-compose.yml` 來同時管理兩個服務，共享 `config.yaml` 配置檔案。

## 🛠️ 開發

### 執行測試

```bash
uv run pytest
```

### 程式碼格式化

```bash
uv run black src/
uv run ruff check src/
```

## 💡 提示

1. **管理介面** (`src/main.py`) - 提供視覺化介面編輯 `config.yaml`，不會實際運行 Discord bot
2. **Discord 監聽器** (`discord_listener.py`) - 實際連接 Discord 並監聽事件的服務，讀取 `config.yaml`
3. **配置檔案** - 所有設定都存在 `config.yaml`，兩個服務共享同一個檔案
4. **修改生效** - 修改配置後，需要重新啟動 `discord_listener.py` 才會生效
5. **首次使用** - Streamlit 會自動生成預設的 `config.yaml`，或手動複製 `config.example.yaml`

## 🔒 安全建議

- ⚠️ **不要將 `config.yaml`（包含真實 Token）提交到版本控制**
- ✅ `config.yaml` 已加入 `.gitignore`
- ✅ 使用 `config.example.yaml` 作為範本分享
- ✅ 定期更換 Bot Token
- ✅ 確保 Webhook URL 的安全性

## 📝 授權

MIT License

## 🆘 支援

如有問題或建議，請開啟 Issue。
