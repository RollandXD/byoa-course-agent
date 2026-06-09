# Experiment 2 BYOA Report Draft

## 1. 基本信息

- 姓名：于重阳
- 学号：2024211429
- GitHub Repo：https://github.com/RollandXD/byoa-course-agent
- 本地项目：`byoa-course-agent`

## 2. Agent 简介

本项目实现了 BYOA Code：一个 Claude Code 风格的终端编码 agent，由 DeepSeek Function Calling 驱动。用户通过 `python -m byoa_agent`（默认进入 chat）获得一个持续多轮对话的 agent shell：模型在回答前会自主调用本地工具读取真实文件，工具调用以 `⏺ tool(args)` 形式实时渲染，回答流式渲染为高亮 Markdown，写文件前展示彩色 diff。系统由四层组成：交互 shell（斜杠命令 + 流式渲染）、会话循环（跨轮上下文记忆 + 上下文压缩）、DeepSeek SSE 客户端（增量重组 tool_calls），以及 11 个沙箱化本地工具——6 个通用编码工具（read_file/write_file/edit_file/list_files/grep_files/run_command）和 5 个课程技能（PPTX/DOCX 提取、上下文搜索、交付自检、日志摘要）。写文件与执行命令必须经过 Claude Code 式权限确认门（y/n/always），全部实现仅用 Python 标准库。

## 3. 运行说明

运行前在 `.env` 中配置 `DEEPSEEK_API_KEY`，然后执行 `python -m byoa_agent` 进入交互 shell。常用命令：`/tools` 查看 11 个工具，`/check` 检查交付状态，`/log` 汇总工具日志，`/report` 生成报告材料，`/auto` 切换写操作自动批准，`/clear` 清空上下文。也可以直接输入自然语言任务，例如“读一下课件里实验二的要求，然后检查这个仓库还缺什么”，agent 会连续调用 `extract_pptx_text`、`check_submission_readiness` 等工具并把调用写入 `runs/latest.jsonl`。当前自检结果为 8/8 项通过，另有 0 项提醒、0 项失败；最近工具日志包含 0 次调用。

## 4. 截图建议

1. `python -m byoa_agent` 启动 banner 加 `/tools`，展示 Claude Code 风格界面和 11 个工具。
2. 自然语言提问“实验二要交什么”，展示 `⏺ extract_pptx_text(...)` 工具轨迹与 Markdown 渲染回答。
3. 让 agent 修改文件，展示批准前的红绿 diff 预览与 `[y/n/a]` 权限确认。
4. `/check` 与 `/log` 输出，展示 PASS/WARN/FAIL 自检和 JSONL 工具调用证据。

## 5. AI 使用反思

本实验使用 AI 辅助完成了从单轮问答工具脚本到 Claude Code 风格多轮 agent 的重构。遇到的具体技术困难包括：流式响应中 tool_calls 以增量分片到达，需要按 index 重组 id/name/arguments，否则 JSON 解析必然失败；早期版本每轮丢弃历史导致 agent 无法引用上一轮的工具结果，重构为持久会话后又必须加上下文压缩防止超长。解决方式是为 SSE 重组和会话记忆分别编写 unittest 固定行为，并用权限门把模型的写操作约束在仓库内。

## 6. 95+ 自查结论

评分证据链：课程要求 -> Claude Code 式架构设计 -> DeepSeek Function Calling 工具 -> 流式交互执行 -> 权限门与沙箱 -> 自检结果 -> 工具日志 -> AI 反思。代码仓库包含 agent 循环、工具注册表、prompt、测试、README 和报告草稿；执行截图可以直接覆盖系统机制、Agent 执行和反思三项评分点。
