# 软件产品综合开发实践（实验二）实验报告填写稿

## 1. 姓名

于重阳

## 2. 学号

2024211429

## 3. Agent 代码仓库

https://github.com/RollandXD/byoa-course-agent

该仓库包含 Agent 主循环、工具注册表、核心 prompt（`prompts/system.md` 和 `prompts/demo.md`）、README、53 个单元测试和报告草稿。

## 4. Agent 简介（不超过 500 字）

我实现的 Agent 叫 BYOA Code：一个 Claude Code 风格的终端编码 agent，由 DeepSeek OpenAI 兼容 Function Calling 驱动，代码只用 Python 标准库。运行 `python -m byoa_agent` 即进入持续多轮对话的 agent shell：模型回答前自主调用本地工具读取真实文件，工具调用以 `⏺` 行实时显示，回答流式渲染为高亮 Markdown，写文件前展示彩色 diff 并按 `[y/n/a]` 确认——交互与 Claude Code 一致。

系统分四层：交互 shell 提供斜杠命令、流式渲染与权限确认；会话循环保存跨轮对话历史，上下文过长时自动压缩旧的工具输出；DeepSeek SSE 客户端把流式响应中分片到达的 tool_calls 增量重组成完整调用；最底层是 11 个沙箱化工具——6 个通用编码工具（读/写/编辑文件、glob 列举、正则搜索、执行命令）加 5 个课程技能（PPTX/DOCX 提取、上下文搜索、交付自检、日志摘要），远超实验要求的 2 个技能。读取限制在课程工作区内，写入和命令限制在仓库内且必须通过权限门，所有调用写入 `runs/latest.jsonl` 形成可审计证据。

【图 1：Agent 结构图，可画为「用户 ❯ 输入 → chat shell（斜杠命令/流式渲染/权限门）→ AgentSession（多轮记忆/上下文压缩）→ DeepSeek Function Calling（SSE）→ 11 个本地工具 → 课件/仓库/命令 → 回答+JSONL 日志」】

## 5. Agent 运行说明（不超过 500 字）

运行前把 `.env.example` 复制为 `.env` 并填入 `DEEPSEEK_API_KEY`，然后执行 `python -m byoa_agent`（chat 是默认命令）进入交互 shell。直接输入自然语言任务，例如「读一下课件里实验二的要求，再检查这个仓库还缺什么」，agent 会自动串联多个工具后作答。斜杠命令：`/tools` 看工具，`/check` 做 PASS/WARN/FAIL 自检，`/log` 汇总日志，`/report` 生成报告，`/auto` 自动批准，`/compact` 压缩上下文；支持 `@文件` 附加、`!命令` 直通、Ctrl+C 中断回滚。非交互可用 ask/check/report/demo/tools 子命令，`--yes` 跳过确认。

报告放 4 张截图：图 2 启动 banner 加 `/tools`，展示界面与 11 个工具；图 3 提问触发 `⏺ extract_pptx_text(...)` 调用并以 Markdown 渲染回答，证明读取了课件第 136-137 页；图 4 让 agent 修改文件时弹出的红绿 diff 与 `[y/n/a]` 确认；图 5 `/check` 8/8 PASS 与 `/log` 的 JSONL 证据摘要。

## 6. 使用 AI 完成实验任务的过程与反思

本次实验我把 AI 当作结对开发助手，经历了两个阶段：先用 AI 快速搭出一个单轮问答式的课程助手，再让它把项目重构成 Claude Code 风格的多轮 agent。样板代码（CLI 子命令、JSON Schema 字典、PPTX/DOCX 解析、测试骨架）AI 生成得又快又好，但每个阶段都暴露了具体的技术坑。

第一个坑是流式协议的语法细节。DeepSeek 的 SSE 流式响应中，tool_calls 不是一次性给出的，而是按 index 分片到达：第一个分片带 id 和函数名，后续分片只带 arguments 的字符串片段。AI 最初生成的代码对每个分片直接做 `json.loads`，必然解析失败。我让它先打印原始 SSE 流观察真实格式，才改成按 index 维护槽位、把 arguments 逐段拼接、流结束后再整体解析的写法，并用伪造的 SSE 分片序列写了单元测试固定这个行为。

第二个坑是上下文管理。最初版本每问一句就丢掉历史，agent 无法引用上一轮的工具结果，完全不像 Claude Code；改成持久会话后，PPTX 全文这类大工具输出又会让上下文迅速膨胀。最终方案是保留全部对话结构，只在总字符数超限时把最旧的大段工具输出替换成压缩占位符，并提供 /compact 手动压缩。终端体验上也有类似的取舍：AI 第一版的 Markdown 渲染要等整段回答缓冲完才输出，破坏了流式效果，最后改成按行渲染的状态机，行内样式即时上色、代码块跨行保持状态。

第三个坑是幻觉与错误假设。AI 曾默认实验一报告和实验二在同一目录（实际课程目录拆成 lab/01 和 lab/02），也曾在文档里提到项目并未使用的 Pydantic 和 pytest。我的对策是把「先查真实状态」做进 agent 本身：路径沙箱、`check_submission_readiness` 自检、JSONL 日志，再用 53 个 unittest 用例锁定关键行为，并在 system prompt 中明确列出「项目事实」禁止模型编造命令。我的体会是：BYOA 的核心不是让模型多说话，而是用工具、沙箱、权限和测试把它的输出约束成可复现、可审计的软件行为。
