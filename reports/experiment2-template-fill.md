# 软件产品综合开发实践（实验二）实验报告填写稿

## 1. 姓名

于重阳

## 2. 学号

2024211429

## 3. Agent 代码仓库

https://github.com/RollandXD/byoa-course-agent

该仓库包含 Agent 主逻辑、工具定义、核心 prompt、README、测试用例和报告草稿。其中核心 prompt 位于 `prompts/system.md` 和 `prompts/demo.md`。

## 4. Agent 简介（不超过 500 字）

我设计的 Agent 是一个面向实验二 BYOA 作业的交互式课程助手，主界面是终端里的 `python -m byoa_agent chat`，形式上接近 Claude Code / Codex CLI 的连续对话 shell。它不是泛泛聊天工具，而是专门服务本次实验交付：读取课程 PPT 和实验报告模板，检查代码仓库是否满足评分要求，汇总工具调用日志，并生成报告材料。

系统结构分为三层：第一层是 CLI 交互界面，负责接收 `/tools`、`/check`、`/log`、`/report` 等命令；第二层是 DeepSeek OpenAI-compatible Function Calling，负责判断是否需要调用工具；第三层是本地工具集合，负责读取文件和生成证据。项目实现了 7 个工具，包括课程文件列举、项目文件检查、PPTX/DOCX 文本提取、上下文搜索、提交自检和日志摘要。这样 Agent 的回答会先连接本地资料和仓库状态，再生成结果，而不是只依赖模型记忆。

【图 1：Agent 结构图，可画为“用户 -> CLI chat -> DeepSeek -> Function Calling -> 本地工具 -> 课件/模板/日志 -> 回答/报告”】

## 5. Agent 运行说明（不超过 500 字）

运行前在项目根目录配置 `.env` 中的 `DEEPSEEK_API_KEY`，再执行 `python -m byoa_agent chat` 进入交互界面。进入后可以使用 `/tools` 查看 7 个工具 schema，使用 `/check` 检查 README、prompt、源码、测试、报告草稿和日志目录是否齐全，使用 `/log` 汇总 `runs/latest.jsonl` 中的工具调用记录，使用 `/report` 生成实验报告材料，也可以直接输入自然语言问题，例如“实验二要交什么”。

建议在报告中放 4 张截图：图 2 为 chat 启动和 `/tools` 输出，证明 Agent 有交互界面和多个工具；图 3 为自然语言提问触发 `extract_pptx_text`，证明它读取了 `Week 13-15.pptx` 第 136-137 页；图 4 为 `/check` 输出 8/8 PASS，证明交付物完整；图 5 为 `/report` 或 `/log` 输出，证明 Agent 能生成报告材料并保留工具调用证据。

## 6. 使用 AI 完成实验任务的过程与反思

本次实验中，我把 AI 当作结对开发助手使用，主要让它帮助我设计 Agent 的整体结构、Function Calling 请求格式、工具 schema、命令行入口、单元测试和报告材料。AI 在生成样板代码方面效率很高，例如 CLI 子命令、JSON Schema 字典、PPTX/DOCX 文本提取函数都可以快速形成初版。但我也发现，如果不让它读取真实文件，它很容易把“看起来合理”的内容写进项目。

开发时遇到的第一个具体问题是文件路径。AI 起初默认实验一报告 DOCX 位于当前实验二目录，可实际课程目录已经拆成 `lab/01` 和 `lab/02`，测试因此直接报 `FileNotFoundError`。我没有简单删掉这个测试，而是让测试同时搜索当前目录和 `lab/01`，这样既保留了身份信息提取能力，也适配了真实课程目录。第二个问题是命令和依赖幻觉。AI 曾倾向于提到 Pydantic、pytest 或某些不存在的运行命令，但项目实际只用了 Python 标准库、unittest 和手写 JSON Schema。如果这些内容写进 README 或报告，老师复现时就会对不上。

为了解决这些问题，我把“先检查真实状态”做成了 Agent 的一部分。项目增加了 `list_project_files`，让模型能看到仓库里到底有哪些文件；增加了 `check_submission_readiness`，用 PASS/WARN/FAIL 检查 README、prompt、源码、测试、报告和日志目录；增加了 `summarize_tool_log`，把 JSONL 调用记录整理成可以放进报告的证据。工具层还限制只能读取课程工作区内的文件，避免路径越界。

最后，我用 unittest 固定关键行为，包括 PPTX/DOCX 提取、工具 schema 数量、CLI 命令、自检结果、报告生成，以及 `Ctrl+C` 退出不会打印 traceback。通过这些处理，我对 AI 生成的代码做了一轮真实工程化约束。我的体会是，BYOA 的重点不是“让大模型多说几句话”，而是给它明确的工具、上下文和验证机制。只有这样，Agent 的输出才更像可复现的软件结果，而不是一次性的聊天回答。
