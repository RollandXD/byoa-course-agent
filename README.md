# BYOA Course Agent

这是“软件产品综合研发实践”实验二的代码仓库：一个由 DeepSeek API 驱动的单用途课程任务智能体。

它的目标不是泛泛聊天，而是读取本地课程资料，帮助完成 **Experiment 2: Bring Your Own Agent (BYOA)** 的要求梳理、实现计划、截图清单和报告草稿。

## Why It Meets The Assignment

课件要求包括：

- **Tool Use / Skills**：agent 至少具备两个不同功能技能。
- **Context Integration (MCP or similar)**：使用 MCP 或标准 LLM function calling，把模型和本地环境/API 连接起来。
- **Vibe Coding Constraint**：使用 AI 快速生成样板代码，把注意力放在 agent 的系统提示词和编排循环上。

本项目采用 **DeepSeek OpenAI-compatible Function Calling** 作为 MCP-like context bridge，并提供五个本地工具：

| Tool | Purpose |
| --- | --- |
| `list_workspace_files` | 列出可读取的课程资料文件 |
| `list_project_files` | 列出本项目仓库文件，帮助 agent 检查交付物 |
| `extract_pptx_text` | 从 PPTX 课件中按页抽取文本 |
| `extract_docx_text` | 从 DOCX 实验报告中抽取段落文本 |
| `search_extracted_context` | 在已加载资料中搜索关键词证据 |

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

查看工具 schema：

```bash
python -m byoa_agent tools
```

运行固定演示流程：

```bash
python -m byoa_agent demo
```

向 agent 提问：

```bash
python -m byoa_agent ask "请根据课件总结实验二交付物和评分点"
```

使用 `uv` 也可以：

```bash
uv run python -m byoa_agent tools
uv run python -m byoa_agent demo
```

## Outputs For The Report

运行 `demo` 后会生成：

- `runs/latest.jsonl`：工具调用日志，适合截图展示 agent 真的调用了外部工具。
- `reports/experiment2-draft.md`：由 DeepSeek 输出保存的报告草稿。

建议报告截图包括：

1. `python -m byoa_agent tools` 输出，展示工具定义。
2. `python -m byoa_agent demo` 运行过程，展示 agent 返回内容。
3. `runs/latest.jsonl`，展示工具名、参数和结果摘要。
4. `reports/experiment2-draft.md`，展示 agent 生成的报告草稿。

## Tests

```bash
python -m unittest discover -s tests
```

测试覆盖：

- PPTX/DOCX 文本抽取。
- DeepSeek OpenAI-compatible 请求体构造。
- 工具 schema 数量和字段。
- 工具路径白名单限制。
- JSONL 工具调用日志。
- 缺少 `DEEPSEEK_API_KEY` 时的清晰错误。
- `python -m byoa_agent tools` 从项目根目录可直接运行。

## Project Structure

```text
byoa-course-agent/
├── byoa_agent/              # local -m runner wrapper
├── src/byoa_agent/          # agent implementation
├── prompts/system.md        # system prompt included in repo
├── reports/                 # generated report draft
├── runs/                    # generated tool-call logs
└── tests/                   # unittest suite
```

## Reflection Seed

报告反思可以围绕一个具体技术障碍写：最初计划使用 MCP，但为了降低协议调试风险，最终采用 DeepSeek 的标准 function calling。AI 在设计工具参数时容易把路径权限、日志证据和课件真实措辞想得过于理想化，因此通过白名单路径校验、JSONL 日志和测试用例把这些问题固定下来。
