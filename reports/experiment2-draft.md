# Experiment 2 BYOA Report Draft

## 1. 基本信息

- 姓名：于重阳
- 学号：2024211429
- GitHub Repo：https://github.com/RollandXD/byoa-course-agent
- 本地项目：`byoa-course-agent`

## 2. Agent 简介

本项目实现了一个面向“软件产品综合研发实践”实验二的交互式 BYOA 课程助手。它采用命令行终端作为交互界面，用户可以通过 `python -m byoa_agent chat` 进入类似 Claude Code / Codex CLI 的连续对话环境，也可以使用 `/tools`、`/check`、`/log`、`/report`、`/demo` 等固定命令获取稳定输出。Agent 的大模型部分使用 DeepSeek Function Calling，本地工具负责读取课程 PPT、实验报告模板、项目仓库文件和 JSONL 工具调用日志。当前项目暴露 7 个工具，超过实验要求的至少 2 个工具，并通过自检工具把 README、prompt、source code、tests、报告草稿和运行日志等交付证据串联起来。

## 3. 运行说明

运行前在 `.env` 中配置 `DEEPSEEK_API_KEY`。常用命令包括：`python -m byoa_agent tools` 查看工具 schema，`python -m byoa_agent chat` 启动交互式 agent shell，`python -m byoa_agent check` 检查交付状态，`python -m byoa_agent report` 生成报告材料，`python -m byoa_agent demo` 运行固定演示流程。运行过程中，Agent 会根据问题选择调用 `extract_pptx_text`、`extract_docx_text`、`check_submission_readiness`、`summarize_tool_log` 等工具，并将工具调用写入 `runs/latest.jsonl`。当前自检结果为 8/8 项通过，另有 0 项提醒、0 项失败；最近工具日志包含 10 次调用。

## 4. 截图建议

1. `python -m byoa_agent chat` 后输入 `/tools`，展示交互式界面和 Function Calling 工具 schema。
2. 在 chat 中提问“实验二要交什么”，展示 `extract_pptx_text` 读取 `Week 13-15.pptx` 的工具调用。
3. 输入 `/check`，展示 PASS/WARN/FAIL 自检结果，证明项目按 rubric 检查交付完整性。
4. 输入 `/report` 或 `/log`，展示工具日志摘要和报告材料生成过程。

## 5. AI 使用反思

本实验中，我使用 AI 辅助搭建 DeepSeek Function Calling 请求、工具 schema、CLI 入口、测试用例和报告材料。过程中遇到的主要问题不是“代码写不出来”，而是 AI 容易根据旧上下文做错误假设：例如早期测试默认实验一报告 DOCX 位于当前实验二目录，但实际课程文件已经拆到 `lab/01` 和 `lab/02`；AI 也曾倾向于提到项目并未使用的 Pydantic、pytest 或不存在的命令。为了解决这些问题，我把 agent 约束为先读取真实项目文件和课程资料，再回答实验要求；同时加入路径白名单、项目自检工具、JSONL 日志摘要和 unittest 验证。这样最终报告中的结论来自真实仓库状态和工具调用证据，而不是模型凭空补全。

## 6. 95+ 自查结论

该项目的评分证据链为：课程要求 -> Agent 设计 -> DeepSeek Function Calling 工具 -> 交互式 CLI 运行 -> 自检结果 -> 工具日志 -> AI 反思。代码仓库包含 agent 逻辑、工具定义、prompt、测试、README 和报告草稿；执行截图可以直接覆盖系统机制、Agent 执行和反思三项评分点。
