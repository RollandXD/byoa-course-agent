# BYOA Agent 95+ Design

## 背景

实验二要求实现一个 Bring Your Own Agent。课件要求 agent 具备至少两个不同工具，使用 MCP 或标准 LLM function calling 连接本地环境或 API，并提交代码仓库、3-4 张执行截图和一段真实的 AI 使用反思。

当前项目已经实现了一个 DeepSeek function-calling 课程任务 agent，具备 PPTX/DOCX 提取、项目文件检查、上下文搜索、CLI 命令和 JSONL 工具调用日志。为了冲刺 95+，项目需要从“一次性命令式 agent”升级为“可连续交互、可自检、可生成报告证据的终端 agent shell”。

## 目标

项目最终定位为：一个类似 Claude Code / Codex CLI 的终端交互式 BYOA 课程助手。

它面向实验二交付场景，帮助学生：

1. 读取课件和报告模板，理解实验二要求。
2. 检查当前代码仓库是否满足评分标准。
3. 连续对话式调用本地工具，留下可截图的执行证据。
4. 汇总工具调用日志，证明 agent 真实使用外部上下文。
5. 生成实验报告中可直接整理的 Agent 简介、运行说明、截图清单和 AI 使用反思素材。

## 非目标

本轮不做 Web UI、桌面应用或完整 DOCX 自动排版。实验评分重点是 agent 机制、工具调用、执行截图和反思文字，终端交互界面更容易展示命令、输出和工具调用证据。

本轮不把项目扩成通用个人助理。agent 仍然保持单用途：服务“软件产品综合研发实践”实验二 BYOA 作业。

## 交互设计

新增命令：

```bash
python -m byoa_agent chat
```

启动后显示简洁欢迎界面和内置命令：

```text
BYOA Course Agent
/tools   查看工具 schema
/check   检查实验二交付状态
/report  生成报告材料
/demo    运行固定演示流程
/help    查看命令说明
/exit    退出

you >
```

普通输入作为自然语言问题交给 agent；斜杠命令走固定流程，保证截图稳定。每次 agent 调用工具时，终端输出简短的工具调用提示，例如：

```text
tool > extract_pptx_text(path="Week 13-15.pptx")
tool > check_submission_readiness()
```

这样报告截图既能展示交互界面，也能展示 Function Calling 和本地工具使用。

## 功能设计

### 1. 现有工具保留并强化

保留现有 5 个工具：

- `list_workspace_files`
- `list_project_files`
- `extract_pptx_text`
- `extract_docx_text`
- `search_extracted_context`

它们用于证明 agent 可以读取本地课程资料、报告模板和项目文件，并从已加载上下文中搜索证据。

### 2. 新增交付自检工具

新增 `check_submission_readiness`，检查以下项目：

- README 是否存在。
- `prompts/system.md` 和 `prompts/demo.md` 是否存在。
- `src/byoa_agent` 下是否有核心实现。
- `tests/` 是否存在。
- 工具 schema 数量是否不少于 2。
- `reports/experiment2-draft.md` 是否存在。
- `runs/latest.jsonl` 是否存在。
- 实验二报告模板是否可读取。

输出使用 `PASS`、`WARN`、`FAIL` 三种状态，并附简短解释。这个工具服务于报告中的“系统机制与工具”部分，也可以作为高分截图之一。

### 3. 新增日志摘要工具

新增 `summarize_tool_log`，读取 `runs/latest.jsonl` 并输出：

- 总工具调用次数。
- 使用过的工具名称。
- 每次调用的参数摘要。
- 成功或失败状态。
- 这段日志可以证明的评分点。

该工具用于把机器可读 JSONL 转成报告可解释材料，支撑“Agent Execution”评分。

### 4. 新增报告生成能力

新增报告生成流程，作为 `/report` 和可选 CLI 命令使用。输出内容按实验二模板组织：

- Agent 简介，控制在 500 字以内。
- Agent 运行说明，控制在 500 字以内。
- 3-4 张截图建议及每张图证明的评分点。
- AI 使用反思素材，强调具体技术障碍和解决过程。

报告内容必须基于真实项目状态生成，不得声称项目使用不存在的依赖或命令。

## 数据流

普通问答的数据流：

1. 用户在 `chat` 中输入问题。
2. `CourseAgent` 将 system prompt、用户输入和工具 schema 发给 DeepSeek。
3. DeepSeek 返回自然语言或 tool calls。
4. `CourseAgent` 调用本地工具并把结果回传给模型。
5. 最终答案输出到终端，同时工具调用写入 `runs/latest.jsonl`。

斜杠命令的数据流：

1. `/tools` 直接打印工具 schema。
2. `/check` 调用自检工具并输出结构化结果。
3. `/report` 运行报告材料生成流程，并保存到 `reports/experiment2-draft.md`。
4. `/demo` 复用固定演示流程，展示课程要求提取、项目自检、日志摘要和报告建议。

## 错误处理

缺少 `DEEPSEEK_API_KEY` 时，CLI 输出清晰错误，并提示配置 `.env`。

本地文件不存在时，工具返回明确错误，不吞掉异常，也不让模型编造内容。

路径读取仍然限制在课程工作区内，避免 agent 读取任意系统文件。

如果日志文件不存在，`summarize_tool_log` 输出 `WARN`，提示先运行 `/demo` 或一次自然语言任务。

如果自检发现缺失项，`check_submission_readiness` 输出可执行的修复建议。

## 测试设计

新增和修复测试以保证交付可靠：

- 修复现有 DOCX 测试的路径假设，使其适配当前 `lab/01` 和 `lab/02` 布局。
- 测试 `chat` 内置命令解析，不需要真实调用 DeepSeek。
- 测试 `check_submission_readiness` 至少能识别 prompt、source、tests、报告草稿和工具数量。
- 测试 `summarize_tool_log` 能读取 JSONL 并输出工具调用摘要。
- 保留 DeepSeek 请求体构造测试，证明 OpenAI-compatible function calling 结构正确。
- 最终验收命令为 `python -m unittest discover -s tests`。

## 报告与截图设计

最终报告围绕这条证据链组织：

课程要求 -> Agent 设计 -> Function Calling 工具 -> 交互式运行 -> 自检结果 -> 工具日志 -> AI 反思。

推荐截图：

1. `python -m byoa_agent chat` 欢迎界面和 `/tools` 输出，证明交互式 agent shell 与工具 schema。
2. `/demo` 或自然语言提问触发 `extract_pptx_text`，证明 agent 读取课程 PPT 上下文。
3. `/check` 输出 PASS/WARN/FAIL 自检结果，证明仓库按 rubric 对齐。
4. `/report` 或 `summarize_tool_log` 输出，证明工具调用日志和报告材料生成。

报告反思重点写一个真实技术障碍：早期实现假设旧实验一 DOCX 位于当前目录，导致测试在新的 `lab/02` 布局下失败；同时 AI 容易幻觉不存在的依赖或命令。解决方式是增加项目文件检查、严格 prompt 约束、路径白名单、自检工具和单元测试，让 agent 输出与真实仓库保持一致。

## 验收标准

实现完成后必须满足：

1. `python -m unittest discover -s tests` 全部通过。
2. `python -m byoa_agent tools` 输出不少于 7 个工具 schema。
3. `python -m byoa_agent chat` 可以启动，并支持 `/help`、`/tools`、`/check`、`/report`、`/demo`、`/exit`。
4. `/check` 能输出结构化自检结果。
5. `/report` 能更新 `reports/experiment2-draft.md`。
6. 新 demo 运行后能生成当前布局下的 `runs/latest.jsonl`。
7. README、prompts、报告草稿与实际命令保持一致。

## 预期评分策略

目标分配：

- System Mechanics & Tooling：39-40 / 40。
- Agent Execution：38-40 / 40。
- Reflection：18-20 / 20。

总分目标为 95+。项目不靠堆砌复杂功能取胜，而是用交互界面、工具调用、自检结果、日志证据和真实反思构成完整评分证据链。
