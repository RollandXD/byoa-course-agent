# BYOA Course Agent

这是“软件产品综合研发实践”实验二的代码仓库：一个由 DeepSeek Function Calling 驱动的交互式终端课程助手。

它不是泛用聊天机器人，也不是网页应用。它的主界面是类似 Claude Code / Codex CLI 的 terminal agent shell，专门帮助完成 **Experiment 2: Bring Your Own Agent (BYOA)** 的要求理解、交付自检、工具调用证据整理和报告材料生成。

## Why It Meets The Assignment

课件要求包括：

- **Tool Use / Skills**：agent 至少具备两个不同功能技能。
- **Context Integration (MCP or similar)**：使用 MCP 或标准 LLM function calling，把模型和本地环境/API 连接起来。
- **Vibe Coding Constraint**：使用 AI 快速生成样板代码，把注意力放在 agent 的系统提示词和编排循环上。

本项目采用 **DeepSeek OpenAI-compatible Function Calling** 作为 MCP-like context bridge，并提供七个本地工具：

| Tool | Purpose |
| --- | --- |
| `list_workspace_files` | 列出可读取的课程资料文件 |
| `list_project_files` | 列出本项目仓库文件，帮助 agent 检查交付物 |
| `extract_pptx_text` | 从 PPTX 课件中按页抽取文本 |
| `extract_docx_text` | 从 DOCX 实验报告或模板中抽取段落文本 |
| `search_extracted_context` | 在已加载资料中搜索关键词证据 |
| `check_submission_readiness` | 按实验二交付要求检查 README、prompt、代码、测试、报告草稿和日志 |
| `summarize_tool_log` | 将 JSONL 工具调用日志整理成报告可解释的证据摘要 |

## Setup

本项目只使用 Python 标准库。推荐 Python 3.11+。

```bash
cd byoa-course-agent
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek API Key。也可以直接在命令前导出环境变量：

```bash
export DEEPSEEK_API_KEY=sk-your-deepseek-api-key
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-v4-flash
```

## Commands

启动交互式终端 agent：

```bash
python -m byoa_agent chat
```

进入后可使用：

```text
/tools   查看工具 schema
/check   检查实验二交付状态
/log     汇总最近工具调用日志
/report  生成报告材料
/demo    运行固定演示流程
/help    查看命令说明
/exit    退出
```

也可以直接运行固定命令：

```bash
python -m byoa_agent tools
python -m byoa_agent check
python -m byoa_agent report
python -m byoa_agent demo
python -m byoa_agent ask "请根据课件总结实验二交付物和评分点"
```

使用 `uv` 也可以：

```bash
uv run python -m byoa_agent chat
uv run python -m byoa_agent check
uv run python -m byoa_agent report
```

## Outputs For The Report

运行 `chat`、`demo` 或自然语言 `ask` 后会生成或更新：

- `runs/latest.jsonl`：工具调用日志，适合截图展示 agent 真的调用了外部工具。
- `reports/experiment2-draft.md`：按实验二模板组织的报告草稿。

建议报告截图包括：

1. `python -m byoa_agent chat` 加 `/tools`，展示交互式 CLI 和 7 个工具 schema。
2. 在 chat 中提问“实验二要交什么”，展示 agent 调用 `extract_pptx_text` 读取课件。
3. `/check` 或 `python -m byoa_agent check`，展示 PASS/WARN/FAIL 自检结果。
4. `/report`、`/log` 或 `runs/latest.jsonl`，展示报告材料生成和工具调用证据。

## Tests

```bash
python -m unittest discover -s tests
```

测试覆盖：

- PPTX/DOCX 文本抽取。
- DeepSeek OpenAI-compatible 请求体构造。
- 7 个工具 schema 和字段。
- 工具路径白名单限制。
- JSONL 工具调用日志和摘要。
- 交付自检工具。
- 无 API key 时的清晰错误。
- `chat`、`check`、`report` 等 CLI 命令的离线可用性。
- `python -m byoa_agent tools` 从项目根目录可直接运行。

## Project Structure

```text
byoa-course-agent/
├── byoa_agent/              # local -m runner wrapper
├── src/byoa_agent/          # agent implementation
│   ├── agent.py             # DeepSeek function-calling orchestration loop
│   ├── chat.py              # interactive terminal shell
│   ├── cli.py               # command-line entrypoint
│   ├── tools.py             # local tools and OpenAI-compatible schemas
│   └── reporting.py         # report material generation
├── prompts/                 # system and demo prompts
├── reports/                 # generated report draft
├── runs/                    # generated tool-call logs
└── tests/                   # unittest suite
```

## Reflection Seed

报告反思可以围绕一个具体技术障碍写：AI 初期容易沿用旧项目布局，假设实验一 DOCX 位于当前实验二目录，也容易幻觉项目使用 Pydantic、pytest 或不存在的命令。最终通过路径白名单、项目文件检查、交付自检工具、JSONL 日志摘要和 unittest，把模型输出约束到真实仓库状态上。
