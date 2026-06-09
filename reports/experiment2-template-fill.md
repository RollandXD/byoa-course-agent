# 软件产品综合开发实践（实验二）实验报告填写稿

## 1. 姓名

于重阳

## 2. 学号

2024211429

## 3. Agent 代码仓库

https://github.com/RollandXD/byoa-course-agent

该仓库包含 Agent 主逻辑、工具定义、核心 prompt、README、测试用例和报告草稿。其中核心 prompt 位于 `prompts/system.md` 和 `prompts/demo.md`。

## 4. Agent 简介（不超过 500 字）

我设计的 Agent 是一个面向实验二 BYOA 作业的交互式课程助手，主界面是终端里的 `python -m byoa_agent chat`，形式上接近 Claude Code / Codex CLI 的连续对话 shell。它的任务不是泛泛聊天，而是围绕本次实验交付工作：读取课程 PPT 和实验报告模板，检查当前代码仓库是否满足评分要求，总结工具调用日志，并生成报告材料。

这个 Agent 使用 DeepSeek 的 OpenAI-compatible Function Calling 连接模型和本地环境，相当于一个轻量的 MCP-like 上下文桥接方式。项目实现了 7 个工具：列出课程资料文件、列出项目文件、提取 PPTX 文本、提取 DOCX 文本、搜索已加载上下文、检查提交完整性、汇总工具调用日志。通过这些工具，Agent 的回答可以基于本地课件、模板和仓库状态，而不是只依赖模型本身的记忆。

【图 1：Agent 结构示意或 `/tools` 输出截图，可展示 Function Calling 工具列表】

## 5. Agent 运行说明（不超过 500 字）

运行前在项目根目录配置 `.env` 中的 `DEEPSEEK_API_KEY`。常用命令包括：`python -m byoa_agent chat` 启动交互界面，`tools` 查看工具 schema，`check` 检查交付状态，`report` 生成报告材料，`demo` 运行固定演示。进入 chat 后，可输入 `/tools`、`/check`、`/log`、`/report`、`/demo`，也可以直接用自然语言提问。

建议放 4 张运行截图：图 1 为 `chat` 启动后执行 `/tools`，证明有交互式 CLI 和 7 个工具；图 2 为询问“实验二要交什么”，展示 `extract_pptx_text` 读取 `Week 13-15.pptx`；图 3 为 `/check` 输出 8/8 PASS，证明仓库、prompt、测试和报告材料齐全；图 4 为 `/report` 或 `/log`，展示报告生成或 JSONL 工具调用证据。

## 6. 使用 AI 完成实验任务的过程与反思

本次实验中，我主要使用 AI 辅助完成 Agent 的脚手架设计、Function Calling 请求结构、工具 schema、命令行入口、单元测试和报告材料整理。AI 的作用比较像一个结对开发助手：它能很快给出初版结构，但很多地方必须再用真实项目状态校验。

开发过程中最明显的问题是，AI 一开始容易沿用旧上下文做假设。例如测试曾默认实验一报告 DOCX 就在当前实验二目录，实际文件已经被整理到 `lab/01` 和 `lab/02` 两个目录中，导致测试直接失败。还有一次，AI 倾向于把项目说成使用了 Pydantic、pytest 或某些不存在的命令，但这个项目实际只用了 Python 标准库、unittest 和手写的 JSON Schema 字典。

我的处理方式是把这些不稳定点工程化固定下来。首先，工具层限制只能读取课程工作区内的文件，避免随意访问路径。其次，我增加了 `list_project_files` 和 `check_submission_readiness`，让 Agent 先检查真实仓库，再回答“项目是否满足实验要求”。再次，所有工具调用会写入 `runs/latest.jsonl`，后续可以用 `summarize_tool_log` 汇总成报告证据。最后，我补充了 unittest，用测试约束 PPTX/DOCX 提取、工具数量、CLI 命令、自检结果和报告生成。

通过这次实验，我的体会是：用 AI 写 Agent 并不只是让模型生成代码，更重要的是给它可验证的上下文、清楚的 prompt 和能暴露错误的测试。否则它很容易把“听起来合理”的内容写进项目里。最终这个 Agent 能够读取本地课件、调用工具、生成日志并自检交付状态，基本符合 BYOA 对工具使用和上下文集成的要求。
