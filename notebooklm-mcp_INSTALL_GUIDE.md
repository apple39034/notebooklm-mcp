# NotebookLM MCP 安装指南

> 适用平台：macOS (Apple Silicon / Intel)  
> 最后更新：2026-05-23（v2：新增下载工具、生成参数升级）

---

## 目录

1. [前置条件](#1-前置条件)
2. [安装步骤](#2-安装步骤)
3. [已知问题与修复](#3-已知问题与修复)
4. [注册到 Claude Code](#4-注册到-claude-code)
5. [注册到 Claude Desktop](#5-注册到-claude-desktop)
6. [验证安装](#6-验证安装)
7. [全部功能与使用示例](#7-全部功能与使用示例)
8. [下载生成内容到本地](#8-下载生成内容到本地)
9. [更新与维护](#9-更新与维护)

---

## 1. 前置条件

### 安装 uv（Python 包管理器）

```bash
# 方式一：curl 安装
curl -LsSf https://astral.sh/uv/install.sh | sh

# 方式二：Homebrew 安装（推荐，路径更稳定）
brew install uv
```

验证安装：

```bash
uv --version
which uv   # 记录此路径，后续配置需要
```

> **注意**：Homebrew 安装路径通常为 `/opt/homebrew/bin/uv`（Apple Silicon）或 `/usr/local/bin/uv`（Intel）。Claude Desktop 无法继承 shell 的 PATH，**必须使用绝对路径**。

---

## 2. 安装步骤

### Step 1：克隆仓库并安装依赖

```bash
# 推荐：使用已修复 bug 并包含下载功能的 fork
git clone https://github.com/apple39034/notebooklm-mcp.git ~/tools/notebooklm-mcp
cd ~/tools/notebooklm-mcp
uv sync
```

> 原始仓库为 `alfredang/notebooklm-mcp`，但存在 `sources_count` 拼写错误且缺少下载工具。推荐使用上方 fork，已包含所有修复。

`uv sync` 会自动创建 `.venv` 虚拟环境，安装所有依赖（包括 `notebooklm-py` 和 `fastmcp`）。

### Step 2：安装 Playwright Chromium 浏览器

**必须使用 uv 虚拟环境内的 playwright 来安装，不能用系统 playwright：**

```bash
cd ~/tools/notebooklm-mcp
uv run playwright install chromium
```

> ⚠️ 如果系统中还有其他 playwright（如 miniconda、pip 全局安装的），它们安装的浏览器版本可能与 venv 内的 playwright 版本不匹配，导致找不到可执行文件。务必用 `uv run playwright install chromium` 而非直接 `playwright install`。

### Step 3：安装 socksio（代理支持）

如果你的 Mac 配置了代理（Clash、V2Ray 等），需额外安装此包，否则服务器启动时会崩溃：

```bash
cd ~/tools/notebooklm-mcp
uv pip install socksio
```

### Step 4：Google 账号登录认证

```bash
cd ~/tools/notebooklm-mcp
uv run notebooklm login
```

执行后会自动打开 Chromium 浏览器：

1. 用 Google 账号登录
2. 若未自动跳转，手动访问 [notebooklm.google.com](https://notebooklm.google.com)
3. 等待终端显示 **"Success"** 后关闭浏览器

认证信息会保存在 `~/.notebooklm/browser_profile`，后续无需重复登录。

**验证认证是否成功：**

```bash
cd ~/tools/notebooklm-mcp
uv run python -c "
from notebooklm import NotebookLMClient
import asyncio
async def test():
    client = await NotebookLMClient.from_storage()
    async with client:
        notebooks = await client.notebooks.list()
        print(f'认证成功！共有 {len(notebooks)} 个 notebooks。')
asyncio.run(test())
"
```

### Step 5：测试服务器是否正常启动

```bash
cd ~/tools/notebooklm-mcp
uv run python server.py
```

期望看到：

```
Starting NotebookLM MCP server...
NotebookLM client initialized successfully
Starting MCP server 'NotebookLM' with transport 'stdio'
```

确认后按 `Ctrl+C` 停止。

---

## 3. 已知问题与修复

### 问题一：`source_count` 属性不存在

**症状**：调用 `list_notebooks` 时报错 `'Notebook' object has no attribute 'source_count'`

**原因**：原始 `server.py` 拼写错误，正确属性名为 `sources_count`（带 s）

**状态**：✅ 使用推荐 fork（`apple39034/notebooklm-mcp`）已自动修复，无需手动处理。

### 问题二：SOCKS 代理导致服务器启动失败

**症状**：服务器报错 `ImportError: Using SOCKS proxy, but the 'socksio' package is not installed`

**修复**：

```bash
cd ~/tools/notebooklm-mcp
uv pip install socksio
```

### 问题三：Chromium 可执行文件不存在

**症状**：登录时报错 `Executable doesn't exist at .../chromium-xxxx/...`

**原因**：运行的是系统/miniconda 的 playwright，而非 venv 内的版本，两者需要的 Chromium 版本号不同

**修复**：

```bash
cd ~/tools/notebooklm-mcp
uv run playwright install chromium   # 使用 venv 内的 playwright
```

---

## 4. 注册到 Claude Code

### 获取实际路径

```bash
which uv          # 例：/opt/homebrew/bin/uv
pwd               # 在 notebooklm-mcp 目录下执行，例：/Users/yourname/tools/notebooklm-mcp
```

### 注册命令（替换为你的实际路径）

```bash
claude mcp add notebooklm -- /opt/homebrew/bin/uv \
  --directory /Users/yourname/tools/notebooklm-mcp \
  run python server.py
```

### 验证

```bash
claude mcp list
# 应看到：notebooklm: ... - ✓ Connected
```

> **注意**：MCP 在当前会话添加后，需**重启 Claude Code 会话**才能在新会话中使用工具。

---

## 5. 注册到 Claude Desktop

打开 Claude Desktop → Settings → Developer → Edit Config，编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "notebooklm": {
      "command": "/opt/homebrew/bin/uv",
      "args": [
        "--directory",
        "/Users/yourname/tools/notebooklm-mcp",
        "run",
        "python",
        "server.py"
      ]
    }
  }
}
```

**替换**：
- `/opt/homebrew/bin/uv` → 你的 `which uv` 输出
- `/Users/yourname/tools/notebooklm-mcp` → 你的实际克隆路径

完全退出 Claude Desktop（`Cmd+Q`）后重新打开，聊天框出现锤子图标说明 MCP 已加载。

---

## 6. 验证安装

在 Claude Code 或 Claude Desktop 中输入：

```
列出我的所有 NotebookLM notebooks
```

能看到你的 notebook 列表即安装成功。

---

## 7. 全部功能与使用示例

### Notebook 管理

#### `list_notebooks` — 列出所有 notebooks
- "列出我的所有 NotebookLM notebooks"
- "我有哪些 notebooks？"

#### `create_notebook` — 创建新 notebook
- "创建一个名为'AI 论文阅读'的 notebook"
- "新建一个 notebook 叫'流行病学方法笔记'"

---

### 添加资料来源

#### `add_source_url` — 添加网页 URL 为资料来源
- "把 https://arxiv.org/abs/2501.xxxxx 添加到 notebook '混合效应模型' 里"
- "将这篇博客文章 URL 加入'MCP 开发指南' notebook"

#### `add_source_text` — 添加纯文本为资料来源
- "把这段论文摘要添加到 notebook 'AI 研究'：[粘贴文本]"
- "将我的会议笔记文本加入'项目规划' notebook"

---

### 与资料对话

#### `ask_notebook` — 基于 notebook 内容提问
- "问 notebook '混合效应模型'：什么是随机斜率模型？"
- "在'MCP 开发指南' notebook 里找：如何处理认证？"

#### `get_notebook_summary` — 获取 notebook 摘要和关键洞察
- "总结 notebook 'Browser Extensions' 的核心内容"
- "给我'混合效应模型' notebook 的关键要点"

---

### 查看生成状态

#### `list_artifacts` — 列出 notebook 所有已生成内容及状态
- "列出 notebook '混合效应模型' 的所有生成内容"
- "查看 notebook xxx 的音频是否已生成完成"

返回字段：`id`、`title`、`kind`、`status`（processing / pending / completed / failed）

---

### 生成内容（AI 创作）

> 生成任务为**异步执行**，触发后用 `list_artifacts` 轮询状态，`completed` 后再下载。

#### `generate_audio_overview` — 生成播客音频
支持参数：`audio_format`（DEEP_DIVE / BRIEF / CRITIQUE / DEBATE）、`audio_length`（SHORT / DEFAULT / LONG）、`language`

- "用 DEBATE 格式、中文为 notebook '混合效应模型' 生成一期播客"
- "生成一期 SHORT 版本的音频概览，notebook id 为 xxx"

#### `generate_video_overview` — 生成视频概览
支持参数：`video_format`（EXPLAINER / BRIEF）、`video_style`（AUTO_SELECT / CLASSIC / WHITEBOARD / KAWAII / ANIME / WATERCOLOR / RETRO_PRINT / HERITAGE / PAPER_CRAFT）、`language`

- "用 WHITEBOARD 风格为 notebook 'MCP 开发指南' 生成视频"
- "生成一个 BRIEF 格式、ANIME 风格的视频概览"

#### `generate_slide_deck` — 生成幻灯片（PPT 风格）
- "为'混合效应模型' notebook 生成演示幻灯片"
- "把'MCP 开发指南'做成一套汇报 slides"

#### `generate_mind_map` — 生成思维导图
- "为'混合效应模型' notebook 生成思维导图"
- "把'Browser Extensions' notebook 的内容做成知识图谱"

#### `generate_infographic` — 生成信息图
支持参数：`orientation`（LANDSCAPE / PORTRAIT / SQUARE）、`detail_level`（CONCISE / STANDARD / DETAILED）、`language`

- "生成一张 PORTRAIT 方向、DETAILED 详细程度的信息图"
- "为 notebook 'MCP 开发' 生成一张横版简洁信息图"

#### `generate_quiz` — 生成测验题
- "为'混合效应模型' notebook 出 10 道测试题"
- "基于'MCP 开发指南'生成一套知识测验"

#### `generate_flashcards` — 生成记忆卡片
- "为'混合效应模型' notebook 生成学习闪卡"
- "把'OpenClaw 部署指南'的关键命令做成闪卡"

#### `generate_summary_report` — 生成摘要报告（简报文档）
- "为'混合效应模型' notebook 生成一份正式摘要报告"
- "把'Browser Extensions' notebook 做成一份简报"

#### `generate_data_table` — 提取数据为表格
- "从'混合效应模型' notebook 中提取所有模型参数到表格"
- "把'Browser Extensions'里提到的扩展和冲突类型整理成表格"

---

### 下载到本地

#### `download_audio` — 下载音频到本地（默认 `~/Downloads`）
- "下载 notebook xxx 的音频"
- "把音频保存到 ~/Documents/podcasts/model.mp3"

#### `download_video` — 下载视频到本地
- "下载 notebook xxx 的视频到 ~/Downloads"
- "把视频概览保存为 ~/Movies/overview.mp4"

#### `download_slide_deck` — 下载幻灯片到本地
- "下载 notebook xxx 的幻灯片"
- "把 slides 保存到 ~/Desktop/presentation.pptx"

---

## 8. 下载生成内容到本地

### 标准工作流

```
1. generate_audio_overview(notebook_id, audio_format="DEBATE", language="zh")
        ↓ 等待几分钟
2. list_artifacts(notebook_id)   → 确认 status = "completed"
        ↓
3. download_audio(notebook_id)   → 保存到 ~/Downloads/<id>_audio.mp3
```

### 各类型下载支持情况

| 内容类型 | MCP 直接下载 | 默认文件名 | 网页端备选 |
|---------|:-----------:|-----------|-----------|
| 音频播客 | ✅ `download_audio` | `<id>_audio.mp3` | Studio → 下载按钮 |
| 视频概览 | ✅ `download_video` | `<id>_video.mp4` | Studio → 播放（暂无下载） |
| 幻灯片 | ✅ `download_slide_deck` | `<id>_slides.pptx` | Studio → 导出 Google Slides |
| 摘要报告 | ❌ 需网页操作 | — | Studio → 复制/下载文档 |
| 信息图 | ❌ 需网页操作 | — | Studio → 右键另存图片 |
| 数据表格 | ❌ 需网页操作 | — | Studio → 复制内容 |
| 思维导图 | ❌ 需网页操作 | — | Studio → 截图/导出 |
| 测验 / 闪卡 | ❌ 需网页操作 | — | 仅网页内交互 |

### 自定义下载路径

下载工具的 `output_path` 参数接受任意本地路径：

```
下载 notebook xxx 的音频，保存到 ~/Documents/podcasts/episode1.mp3
```

### 批量触发建议

用 MCP 一次触发多个生成任务，等待完成后统一下载：

```
分别为以下三个 notebooks 生成 DEEP_DIVE 格式播客：
- notebook id: xxx（混合效应模型）
- notebook id: yyy（MCP 开发指南）
- notebook id: zzz（Browser Extensions）
```

---

## 9. 更新与维护

### 更新 notebooklm 库

```bash
cd ~/tools/notebooklm-mcp
uv sync --upgrade
```

### 重新登录（Cookie 过期时）

```bash
cd ~/tools/notebooklm-mcp
uv run notebooklm login
```

### 移除并重新注册 MCP（排查连接问题）

```bash
claude mcp remove notebooklm
claude mcp add notebooklm -- /opt/homebrew/bin/uv \
  --directory /Users/yourname/tools/notebooklm-mcp \
  run python server.py
```

### 查看服务器日志（Claude Desktop）

```bash
tail -100 ~/Library/Logs/Claude/mcp*.log
```

---

## 附：项目结构

```
notebooklm-mcp/
├── server.py                        # MCP 服务器（已修复 bug，含下载工具）
├── pyproject.toml                   # 项目依赖
├── README.md                        # 官方文档（英文）
├── notebooklm-mcp_INSTALL_GUIDE.md  # 本安装指南（中文）
└── .venv/                           # 虚拟环境（自动创建，勿提交 git）
```

认证数据保存位置：`~/.notebooklm/browser_profile`
