# BYOA Code

这是「软件产品综合研发实践」实验二（Bring Your Own Agent）的代码仓库：**BYOA Code**，一个 Claude Code 风格的终端编码 agent，由 DeepSeek Function Calling 驱动。

它不是泛用聊天机器人，也不是网页应用。运行 `python -m byoa_agent` 直接进入一个持续多轮对话的 agent shell：模型在回答前会自主调用本地工具读取真实文件、搜索代码、执行命令，工具调用以 `⏺ tool(args)` 形式实时渲染，回答流式渲染为高亮 Markdown，写文件前展示彩色 diff 并等待权限确认——与 Claude Code 的交互方式一致。

## 终端体验

- **流式 Markdown 渲染**：标题、粗体、行内代码、代码块边框、列表、引用、表格全部 ANSI 高亮，边流式边渲染。
- **思考动画**：等待模型时显示 `✻ 思考中… (2.3s)` spinner，输出到达即清除。
- **diff 权限预览**：`write_file` / `edit_file` 在批准前先展示红绿 unified diff，新文件展示内容预览。
- **回合状态栏**：每轮结束显示 `⏱ 耗时 · ⚒ 工具调用数 · ◔ 上下文占用%`。
- **`@文件` 引用**：在输入里写 `@README.md` 自动把文件内容附加进提问。
- **`!命令` 直通**：`!git status` 绕过模型直接执行 shell 命令。
- **Ctrl+C 中断**：打断当前回合并回滚本轮消息，而不是退出 shell；空提示符下 Ctrl+C 才退出。
- **readline 历史**：方向键翻阅历史输入，持久化在 `~/.byoa_code_history`。
- **CJK 对齐 banner**：按东亚字宽计算的圆角启动框。

## 架构

```
用户 ❯ 输入
  └─ chat shell（斜杠命令 + 流式渲染 + 权限确认）
       └─ AgentSession（跨轮对话记忆 + 工具循环 + 上下文压缩）
            └─ DeepSeekClient（OpenAI 兼容 Function Calling + SSE 流式增量重组）
                 └─ AgentToolbox（11 个沙箱化本地工具 + JSONL 调用日志）
```

满足课件实验二的硬性要求：

- **Tool Use / Skills**：11 个工具，远超「至少两个不同功能技能」。
- **Context Integration（MCP or similar）**：使用 DeepSeek 的 OpenAI 兼容 Function Calling 作为模型与本地环境的标准化桥接。
- **Vibe Coding Constraint**：样板代码由 AI 生成，精力集中在系统提示词与编排循环上。

## 工具

通用编码工具（Claude Code 风格）：

| Tool | Purpose |
| --- | --- |
| `read_file` | 读取 workspace 内文本文件（支持 offset/limit） |
| `write_file` | 在仓库内创建/覆盖文件（需权限确认） |
| `edit_file` | 精确替换文件片段，要求唯一匹配（需权限确认） |
| `list_files` | 按 glob 模式列出 workspace 文件 |
| `grep_files` | 按正则搜索文本文件内容 |
| `run_command` | 在仓库内执行 shell 命令，如跑测试（需权限确认） |

课程任务技能：

| Tool | Purpose |
| --- | --- |
| `extract_pptx_text` | 从 PPTX 课件按页抽取文本 |
| `extract_docx_text` | 从 DOCX 报告或模板抽取段落文本 |
| `search_extracted_context` | 在已加载课件资料中搜索关键词 |
| `check_submission_readiness` | 按实验二交付要求做 PASS/WARN/FAIL 自检 |
| `summarize_tool_log` | 将 JSONL 工具调用日志整理成报告证据 |

**沙箱与权限**：读取限制在课程 workspace 内；写入和命令执行限制在本仓库内，且必须通过权限门（`[y/n/a]` 确认，`a` 为本次会话始终允许，`/auto` 可切换）。

## Setup

本项目只使用 Python 标准库。推荐 Python 3.11+。

```bash
cd byoa-course-agent
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek API Key。也可以直接导出环境变量：

```bash
export DEEPSEEK_API_KEY=sk-your-deepseek-api-key
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-v4-flash
```

## 使用

启动交互式 agent shell（默认命令）：

```bash
python -m byoa_agent
```

进入后直接输入自然语言任务，例如「读一下课件里实验二的要求，然后检查这个仓库还缺什么」。斜杠命令：

```text
/tools    查看工具列表
/check    检查实验二交付状态
/log      汇总最近工具调用日志
/report   生成报告材料
/demo     运行固定演示流程
/clear    清空对话上下文
/compact  压缩历史工具输出
/auto     切换写操作自动批准
/context  查看上下文用量
/help     查看命令说明
/exit     退出

@文件名   把文本文件内容附加进提问，例如：@README.md 帮我精简这份文档
!命令     绕过模型直接执行 shell 命令，例如：!git status
```

非交互命令：

```bash
python -m byoa_agent tools                 # 打印全部工具 schema
python -m byoa_agent check                 # 交付自检（离线可用）
python -m byoa_agent report                # 生成报告材料（离线可用）
python -m byoa_agent demo                  # 固定演示流程
python -m byoa_agent ask "实验二要交什么"   # 单次提问
python -m byoa_agent --yes ask "把测试跑一遍"  # 自动批准写操作/命令
```

使用 `uv` 时在所有命令前加 `uv run` 即可。

## Outputs For The Report

- `runs/latest.jsonl`：工具调用日志，证明 agent 真实调用了外部工具。
- `reports/experiment2-draft.md`：按实验二模板组织的报告草稿（`/report` 生成）。
- `reports/experiment2-template-fill.md`：可直接粘贴进官方 DOCX 模板的填写稿。

建议报告截图：

1. `python -m byoa_agent` 启动 banner + `/tools`，展示 Claude Code 风格界面和 11 个工具。
2. 自然语言提问「实验二要交什么」，展示 `✻ 思考中` spinner、`⏺ extract_pptx_text(...)` 工具轨迹和 Markdown 渲染的回答。
3. 让 agent 修改文件，展示批准前的红绿 diff 预览与 `[y/n/a]` 权限确认。
4. `/check` 与 `/log`，展示 PASS/WARN/FAIL 自检和 JSONL 工具调用证据。

## Tests

```bash
python -m unittest discover -s tests
```

75 个用例覆盖：工具沙箱与权限门、diff 预览、SSE 流式增量重组、会话记忆与上下文压缩、中断回滚、Markdown 渲染、斜杠命令、`@文件`/`!命令`、CLI 冒烟和报告生成。
