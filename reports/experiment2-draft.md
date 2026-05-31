# Experiment 2 BYOA Report Draft

非常好！所有信息已收集完毕。以下是根据课程材料（来源：`Week 13-15.pptx` 第136-137页）和项目仓库分析的完整演示结果。

---

## 🧪 实验2 完整演示结果

### 一、实验要求摘要（来源：Week 13-15.pptx，第136-137页）

**实验名称：** Bring Your Own Agent (BYOA)

**核心目标：** 使用 *Vibe Coding*（借助 Cursor/Codex 等 AI 工具）快速搭建一个**单用途 AI Agent**，该 Agent 必须依赖**外部工具/上下文**（而非仅靠 LLM 的基座知识）。

**三项技术要求（Must-Haves）：**

| 要求 | 描述 |
|------|------|
| ① 工具使用 / 技能 | Agent 必须配备**至少两个不同的功能工具** |
| ② 上下文集成 | 使用 **MCP 或标准 LLM Function Calling** 桥接 Agent 与本地环境/API |
| ③ Vibe Coding 约束 | 必须使用 AI 编写样板代码，专注于 System Prompt 和编排逻辑 |

**评分标准（Rubric）— 总分100分：**
- **系统机制与工具（代码仓库，含所有 Prompts）**：40分
- **Agent 执行（报告截图）**：40分
- **反思（报告文字）**：20分 — 要求诚实地指出 AI 遇到的具体技术障碍及解决过程

**截止日期：** 2026/06/20 23:59:59

**交付物：**
1. 代码仓库（Agent 逻辑 + 工具定义）
2. 简短报告（≤5页，含 3~4 张执行截图 + 一段反思）

---

### 二、项目仓库检查清单（基于本地文件分析）

| 类别 | 文件/内容 | 状态 | 说明 |
|------|-----------|------|------|
| **Agent 逻辑** | `src/byoa_agent/agent.py` | ✅ 已实现 | 主循环 + Tool Call 编排 |
| **工具定义** | `src/byoa_agent/tools.py` | ✅ 已实现 | 5 个本地工具（远超要求的≥2个） |
| **DeepSeek Function Calling** | `src/byoa_agent/deepseek.py` | ✅ 已实现 | 使用 OpenAI 兼容接口 + JSON Schema |
| **CLI 入口** | `src/byoa_agent/cli.py` | ✅ 已实现 | 支持 `tools` / `demo` / `ask` 三个子命令 |
| **配置文件** | `src/byoa_agent/config.py` | ✅ 已实现 | 从 .env 加载 API Key |
| **System Prompt** | `prompts/system.md` | ✅ 已实现 | Agent 角色/规则定义 |
| **Demo Prompt** | `prompts/demo.md` | ✅ 已实现 | 演示用提示模板 |
| **单元测试** | `tests/` 下3个文件 | ✅ 已实现 | CLI、提取器、工具各一套测试 |
| **README** | `README.md` | ✅ 已实现 | 项目说明 |
| **AGENTS.md** | `AGENTS.md` | ✅ 已实现 | 供 AI IDE 读取的配置指南 |
| **报告草稿** | `reports/experiment2-draft.md` | ✅ 已有初稿 | 需润色和补充截图 |
| **运行记录** | `runs/latest.jsonl` | ✅ 已有执行记录 | 演示已运行过 |

**❌ 待完成项：**
1. **更新 `.env`** — 将 `.env.example` 复制为 `.env` 并填入你的 DeepSeek API Key
2. **运行完整 demo** — 执行 `python -m byoa_agent demo` 获取终端输出截图
3. **运行 `ask` 命令做额外交互** — 例如 `python -m byoa_agent ask "列出当前工作区所有课程文件并总结"` 获取更多截图
4. **运行测试** — `python -m unittest discover -s tests` 截图证明测试通过
5. **润色报告** — 补充 3~4 张截图、完善反思段落
6. **提交至公共 GitHub 仓库**

---

### 三、截图建议（3~4 张）

根据实际可运行的命令，建议截取以下画面：

| 序号 | 截图内容 | 执行命令 | 对应 Rubric 维度 |
|------|----------|----------|-----------------|
| ① | **工具列表展示** | `python -m byoa_agent tools` | 展示≥2个工具（系统机制 +40分） |
| ② | **全流程 Demo 执行** | `python -m byoa_agent demo` | 展示 Agent 端到端执行（执行截图 +40分） |
| ③ | **交互式问答** | `python -m byoa_agent ask "列出工作区课程文件并提取实验要求"` | 展示 Function Calling 实际调用过程 |
| ④ | **测试通过** | `python -m unittest discover -s tests` | 展示代码质量（加分印象） |

> 💡 建议截取终端**完整输出**，确保能看到 Tool Call 的请求/响应轮次，而非仅有最终结果。

---

### 四、中文 Markdown 报告草稿大纲

根据实验1 DOCX 中已识别信息（**于重阳 / 2024211429 / github.com/RollandXD**），推荐报告结构如下：

```markdown
# 综合实践（阶段1）— 实验2 — BYOA 课程任务助手

## 1. 基本信息
- **姓名：** 于重阳
- **学号：** 2024211429
- **GitHub：** https://github.com/RollandXD/byoa-course-agent

## 2. 项目概述
本项目构建了一个单用途 AI Agent——“课程任务助手”，
专为回答实验2课程问题而设计。
Agent 通过 DeepSeek Function Calling 调用5个本地工具，
从 PPTX/DOCX 中提取内容并检索。

## 3. 架构与工具
- **通信协议：** DeepSeek OpenAI 兼容 Function Calling
- **工具列表：**
  - `list_workspace_files` — 列出工作区文件
  - `list_project_files` — 列出项目仓库文件
  - `extract_pptx_text` — 提取 PPTX 课件文字
  - `extract_docx_text` — 提取 DOCX 报告文字
  - `search_extracted_context` — 全文检索已加载内容
- **AI 辅助开发：** 使用 Cursor/Codex 编写 Function Calling 脚手架、
  JSON Schema 定义和工具封装代码

## 4. 执行截图（3~4 张）
> [插入截图①：python -m byoa_agent tools]
> [插入截图②：python -m byoa_agent demo 完整输出]
> [插入截图③：python -m byoa_agent ask 交互问答]
> [可选截图④：python -m unittest discover -s tests 测试通过]

## 5. 技术反思（~300字）
> 示例内容：
> 在开发过程中，AI 曾经把本项目实际没有使用的 Pydantic、
> pytest 和不存在的裸命令 `python -m byoa_agent` 写进输出。
> 我通过增加 `list_project_files` 工具，让模型先读取真实仓库结构，
> 并在 System Prompt 中明确说明支持的命令、测试命令和 JSON Schema 实现方式，
> 最终让 Agent 的输出与真实代码保持一致。

## 6. 自查清单
- [x] ≥2 个功能工具（共5个）
- [x] Function Calling 集成
- [x] AI 辅助代码生成
- [x] 代码仓库完整（含 Prompts、测试、README）
- [x] 报告 ≤5 页，含截图 + 反思
```

---

### 五、一句话总结

> **你的项目已满足实验2全部技术要求**（5个工具、DeepSeek Function Calling、AI 辅助开发），**当前只需补充 `.env` 配置、运行演示获取截图、润色反思报告，然后推送到公共 GitHub 仓库即可提交。** 🚀
