# BYOA Agent Chat 95+ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing BYOA course agent into an interactive terminal agent shell with submission self-checking, tool-log summaries, report material generation, updated tests, and 95+ report evidence.

**Architecture:** Keep the current standard-library Python package and DeepSeek OpenAI-compatible function-calling loop. Add focused local tools for scoring evidence, a deterministic chat shell for slash commands, and report-generation helpers that reuse real project state instead of inventing claims.

**Tech Stack:** Python standard library, `argparse`, `unittest`, JSONL logs, DOCX/PPTX zip/XML extraction, DeepSeek OpenAI-compatible chat completions.

---

## File Structure

- Modify `src/byoa_agent/tools.py`: add schemas and implementations for `check_submission_readiness` and `summarize_tool_log`.
- Modify `src/byoa_agent/agent.py`: expose optional tool-call observer callback so the chat UI can print `tool > ...` lines.
- Modify `src/byoa_agent/reporting.py`: add deterministic report-section generation for the experiment template.
- Create `src/byoa_agent/chat.py`: terminal shell, slash-command routing, and interactive loop.
- Modify `src/byoa_agent/cli.py`: add `chat`, `check`, and `report` subcommands while keeping existing `tools`, `demo`, and `ask`.
- Modify `prompts/system.md` and `prompts/demo.md`: align prompts with chat shell, self-check, log summary, and report-generation tools.
- Modify `README.md`: document the final interface, commands, screenshots, and 95+ scoring evidence.
- Modify `reports/experiment2-draft.md`: replace the old AI-looking draft with a concise formal report draft based on the final project.
- Modify `tests/test_extractors.py`: fix the previous-report path assumption for the current `lab/01` and `lab/02` layout.
- Modify `tests/test_tools.py`: cover the new self-check and log-summary tools.
- Modify `tests/test_cli_and_deepseek.py`: cover new CLI commands that do not require a real DeepSeek API key.
- Create `tests/test_chat.py`: cover slash-command parsing and deterministic chat behavior without network calls.

## Task 1: Repair Current Test Baseline

**Files:**
- Modify: `tests/test_extractors.py`

- [ ] **Step 1: Write the failing-path-aware test update**

Replace the current hard-coded experiment 1 path with a helper that searches known course-layout locations:

```python
def previous_report_path() -> Path:
    candidates = [
        COURSE_ROOT / "综合实践（阶段1）-实验1-于重阳-2024211429.docx",
        COURSE_ROOT.parent / "01" / "综合实践（阶段1）-实验1-于重阳-2024211429.docx",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise AssertionError("previous experiment report DOCX was not found")
```

Use it inside `test_docx_extraction_finds_previous_report_identity`:

```python
text = extract_docx_text(previous_report_path())
```

- [ ] **Step 2: Run the focused test**

Run:

```bash
python -m unittest tests.test_extractors
```

Expected before the fix: `FileNotFoundError` for the old `lab/02` path.

Expected after the fix: `OK`.

- [ ] **Step 3: Run the whole suite**

Run:

```bash
python -m unittest discover -s tests
```

Expected: all existing tests pass before adding new features.

- [ ] **Step 4: Commit**

```bash
git add tests/test_extractors.py
git commit -m "test: support current course lab layout"
```

## Task 2: Add Scoring Evidence Tools

**Files:**
- Modify: `src/byoa_agent/tools.py`
- Modify: `tests/test_tools.py`

- [ ] **Step 1: Write tests for new tool schemas**

Add assertions to `ToolSchemaTests.test_tool_schemas_expose_at_least_four_distinct_skills`:

```python
self.assertIn("check_submission_readiness", names)
self.assertIn("summarize_tool_log", names)
self.assertGreaterEqual(len(names), 7)
```

- [ ] **Step 2: Write tests for `check_submission_readiness`**

Add:

```python
def test_submission_readiness_reports_project_evidence(self):
    tools = CourseAgentTools(COURSE_ROOT, project_root=ROOT)

    result = tools.check_submission_readiness({})
    payload = json.loads(result)
    checks = {item["id"]: item for item in payload["checks"]}

    self.assertEqual(payload["summary"]["total"], len(payload["checks"]))
    self.assertEqual(checks["readme"]["status"], "PASS")
    self.assertEqual(checks["prompts"]["status"], "PASS")
    self.assertEqual(checks["source"]["status"], "PASS")
    self.assertEqual(checks["tests"]["status"], "PASS")
    self.assertEqual(checks["tool_count"]["status"], "PASS")
```

- [ ] **Step 3: Write tests for `summarize_tool_log`**

Add:

```python
def test_tool_log_summary_counts_jsonl_entries(self):
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)
        log_path = project_root / "latest.jsonl"
        log_path.write_text(
            "\n".join(
                [
                    json.dumps({"tool": "list_workspace_files", "arguments": {"pattern": "*.pptx"}, "status": "ok"}),
                    json.dumps({"tool": "extract_pptx_text", "arguments": {"path": "Week 13-15.pptx"}, "status": "ok"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        tools = CourseAgentTools(COURSE_ROOT, project_root=project_root, log_path=log_path)

        result = tools.summarize_tool_log({"path": "latest.jsonl", "limit": 5})
        payload = json.loads(result)

        self.assertEqual(payload["summary"]["total_calls"], 2)
        self.assertIn("extract_pptx_text", payload["summary"]["tools_used"])
        self.assertEqual(payload["calls"][0]["status"], "ok")
```

- [ ] **Step 4: Run tests and verify they fail**

Run:

```bash
python -m unittest tests.test_tools
```

Expected: failures mentioning missing `check_submission_readiness` and `summarize_tool_log`.

- [ ] **Step 5: Add tool schemas**

In `create_tool_schemas`, append:

```python
_schema(
    "check_submission_readiness",
    "Check whether this BYOA project has the repository artifacts required for Experiment 2 submission.",
    {},
    [],
),
_schema(
    "summarize_tool_log",
    "Summarize JSONL tool-call logs into report-friendly execution evidence.",
    {
        "path": {
            "type": "string",
            "description": "Project-relative path to a JSONL tool log such as runs/latest.jsonl.",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of calls to include in the summary.",
            "minimum": 1,
            "maximum": 20,
        },
    },
    ["path", "limit"],
),
```

- [ ] **Step 6: Add dispatch entries**

In `CourseAgentTools.dispatch`, add:

```python
"check_submission_readiness": self.check_submission_readiness,
"summarize_tool_log": self.summarize_tool_log,
```

- [ ] **Step 7: Implement helper methods**

Add focused helpers to `CourseAgentTools`:

```python
def _project_path(self, relative: str) -> Path:
    assert self.project_root is not None
    return self.project_root / relative

def _status(self, condition: bool, warn: bool = False) -> str:
    if condition:
        return "PASS"
    return "WARN" if warn else "FAIL"
```

- [ ] **Step 8: Implement `check_submission_readiness`**

Add:

```python
def check_submission_readiness(self, arguments: dict) -> str:
    schemas = create_tool_schemas()
    checks = [
        self._check("readme", "README.md exists", self._project_path("README.md").is_file(), "README documents the agent interface."),
        self._check(
            "prompts",
            "Prompt files exist",
            self._project_path("prompts/system.md").is_file() and self._project_path("prompts/demo.md").is_file(),
            "System and demo prompts are included for grading.",
        ),
        self._check("source", "Source package exists", self._project_path("src/byoa_agent").is_dir(), "Agent implementation is present."),
        self._check("tests", "Unit tests exist", self._project_path("tests").is_dir(), "Tests can be run with unittest."),
        self._check("tool_count", "At least two tool schemas exist", len(schemas) >= 2, f"{len(schemas)} tool schemas are available."),
        self._check("report_draft", "Report draft exists", self._project_path("reports/experiment2-draft.md").is_file(), "Report material is present.", warn=True),
        self._check("tool_log", "Tool log exists", self._project_path("runs/latest.jsonl").is_file(), "Run /demo or chat once to refresh logs.", warn=True),
        self._check("template", "Experiment 2 template exists", (self.workspace / "综合实践（阶段1）-实验2-实验报告模版.docx").is_file(), "The official report template is readable.", warn=True),
    ]
    summary = {
        "total": len(checks),
        "pass": sum(1 for item in checks if item["status"] == "PASS"),
        "warn": sum(1 for item in checks if item["status"] == "WARN"),
        "fail": sum(1 for item in checks if item["status"] == "FAIL"),
    }
    result = json.dumps({"summary": summary, "checks": checks}, ensure_ascii=False, indent=2)
    self._log("check_submission_readiness", arguments, "ok", result)
    return result

def _check(self, check_id: str, label: str, condition: bool, detail: str, warn: bool = False) -> dict:
    return {
        "id": check_id,
        "label": label,
        "status": self._status(condition, warn=warn),
        "detail": detail,
    }
```

- [ ] **Step 9: Implement `summarize_tool_log`**

Add:

```python
def summarize_tool_log(self, arguments: dict) -> str:
    raw_path = str(arguments.get("path") or "runs/latest.jsonl")
    limit = int(arguments.get("limit", 10))
    log_path = self._resolve_project_file(raw_path, ".jsonl")
    calls = []
    if not log_path.exists():
        result = json.dumps(
            {
                "summary": {"total_calls": 0, "tools_used": [], "status": "WARN"},
                "calls": [],
                "message": f"tool log not found: {raw_path}",
            },
            ensure_ascii=False,
            indent=2,
        )
        self._log("summarize_tool_log", arguments, "ok", result)
        return result
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        calls.append(
            {
                "tool": entry.get("tool"),
                "arguments": entry.get("arguments", {}),
                "status": entry.get("status", "unknown"),
                "evidence": self._evidence_for_tool(str(entry.get("tool", ""))),
            }
        )
    limited = calls[:limit]
    summary = {
        "total_calls": len(calls),
        "shown_calls": len(limited),
        "tools_used": sorted({str(call["tool"]) for call in calls if call.get("tool")}),
        "status": "PASS" if calls else "WARN",
    }
    result = json.dumps({"summary": summary, "calls": limited}, ensure_ascii=False, indent=2)
    self._log("summarize_tool_log", arguments, "ok", result)
    return result
```

Add:

```python
def _resolve_project_file(self, value: str, suffix: str) -> Path:
    assert self.project_root is not None
    path = (self.project_root / value).resolve()
    try:
        path.relative_to(self.project_root)
    except ValueError as exc:
        raise ToolError(f"path is outside project: {value}") from exc
    if path.suffix.lower() != suffix:
        raise ToolError(f"expected a {suffix} file: {value}")
    return path

def _evidence_for_tool(self, tool_name: str) -> str:
    evidence = {
        "list_workspace_files": "Shows the agent can inspect local course files.",
        "list_project_files": "Shows the agent can inspect its own repository artifacts.",
        "extract_pptx_text": "Shows the agent reads course PPT context instead of relying on memory.",
        "extract_docx_text": "Shows the agent reads report templates or previous reports.",
        "search_extracted_context": "Shows the agent searches previously loaded context.",
        "check_submission_readiness": "Shows the agent checks the submission against rubric evidence.",
        "summarize_tool_log": "Shows the agent can explain its tool-use trace.",
    }
    return evidence.get(tool_name, "Shows an external tool call was recorded.")
```

- [ ] **Step 10: Run tests**

Run:

```bash
python -m unittest tests.test_tools
python -m unittest discover -s tests
```

Expected: `OK`.

- [ ] **Step 11: Commit**

```bash
git add src/byoa_agent/tools.py tests/test_tools.py
git commit -m "feat: add BYOA submission evidence tools"
```

## Task 3: Add Interactive Chat Shell

**Files:**
- Modify: `src/byoa_agent/agent.py`
- Create: `src/byoa_agent/chat.py`
- Modify: `src/byoa_agent/cli.py`
- Create: `tests/test_chat.py`
- Modify: `tests/test_cli_and_deepseek.py`

- [ ] **Step 1: Write chat tests**

Create `tests/test_chat.py`:

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.chat import ChatSession, render_check_result, render_help
from byoa_agent.tools import CourseAgentTools

COURSE_ROOT = ROOT.parent


class ChatRenderTests(unittest.TestCase):
    def test_help_mentions_core_commands(self):
        text = render_help()

        self.assertIn("/tools", text)
        self.assertIn("/check", text)
        self.assertIn("/report", text)
        self.assertIn("/exit", text)

    def test_check_renderer_formats_status_lines(self):
        payload = {
            "summary": {"total": 1, "pass": 1, "warn": 0, "fail": 0},
            "checks": [{"id": "readme", "label": "README.md exists", "status": "PASS", "detail": "ok"}],
        }

        text = render_check_result(json.dumps(payload, ensure_ascii=False))

        self.assertIn("[PASS] README.md exists", text)
        self.assertIn("1/1", text)


class ChatSessionTests(unittest.TestCase):
    def test_slash_tools_prints_schema_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = ChatSession(
                agent=None,
                tools=CourseAgentTools(COURSE_ROOT, project_root=ROOT),
                project_root=ROOT,
                output=[],
            )

            keep_running = session.handle_line("/tools")

        self.assertTrue(keep_running)
        self.assertIn("list_workspace_files", "\n".join(session.output))

    def test_slash_exit_stops_loop(self):
        session = ChatSession(agent=None, tools=CourseAgentTools(COURSE_ROOT, project_root=ROOT), project_root=ROOT, output=[])

        keep_running = session.handle_line("/exit")

        self.assertFalse(keep_running)
```

- [ ] **Step 2: Run chat tests and verify failure**

Run:

```bash
python -m unittest tests.test_chat
```

Expected: import failure for missing `byoa_agent.chat`.

- [ ] **Step 3: Add tool-call observer to `CourseAgent`**

In `CourseAgent.__init__`, add:

```python
tool_observer: Callable[[str, dict], None] | None = None,
```

Store it:

```python
self.tool_observer = tool_observer
```

Import `Callable`:

```python
from typing import Any, Callable
```

Before dispatching each tool call in `run`, after parsing arguments:

```python
if self.tool_observer is not None:
    self.tool_observer(tool_name, arguments)
```

- [ ] **Step 4: Create `src/byoa_agent/chat.py`**

Add:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .reporting import generate_report_materials, save_report_draft
from .tools import CourseAgentTools, create_tool_schemas


class RunnableAgent(Protocol):
    def run(self, user_prompt: str, max_turns: int = 8) -> str:
        ...


def render_help() -> str:
    return "\n".join(
        [
            "BYOA Course Agent commands:",
            "/tools   查看工具 schema",
            "/check   检查实验二交付状态",
            "/report  生成报告材料",
            "/demo    运行固定演示流程",
            "/help    查看命令说明",
            "/exit    退出",
        ]
    )


def render_check_result(raw_json: str) -> str:
    payload = json.loads(raw_json)
    summary = payload["summary"]
    lines = [
        f"BYOA Submission Check: {summary['pass']}/{summary['total']} PASS, {summary['warn']} WARN, {summary['fail']} FAIL"
    ]
    for item in payload["checks"]:
        lines.append(f"[{item['status']}] {item['label']} - {item['detail']}")
    return "\n".join(lines)


def render_tool_log_summary(raw_json: str) -> str:
    payload = json.loads(raw_json)
    summary = payload["summary"]
    lines = [
        f"Tool Log Summary: {summary['total_calls']} calls, tools={', '.join(summary['tools_used']) or 'none'}"
    ]
    for call in payload["calls"]:
        lines.append(f"- {call['tool']} {call['arguments']} [{call['status']}]")
        lines.append(f"  evidence: {call['evidence']}")
    return "\n".join(lines)


class ChatSession:
    def __init__(
        self,
        agent: RunnableAgent | None,
        tools: CourseAgentTools,
        project_root: Path,
        output: list[str] | None = None,
    ) -> None:
        self.agent = agent
        self.tools = tools
        self.project_root = project_root
        self.output = output if output is not None else []

    def write(self, text: str) -> None:
        self.output.append(text)
        print(text)

    def handle_line(self, line: str) -> bool:
        command = line.strip()
        if not command:
            return True
        if command == "/exit":
            self.write("bye")
            return False
        if command == "/help":
            self.write(render_help())
            return True
        if command == "/tools":
            self.write(json.dumps(create_tool_schemas(), ensure_ascii=False, indent=2))
            return True
        if command == "/check":
            self.write(render_check_result(self.tools.check_submission_readiness({})))
            return True
        if command == "/report":
            material = generate_report_materials(self.project_root, self.tools)
            path = save_report_draft(self.project_root, material)
            self.write(material)
            self.write(f"[report draft] {path}")
            return True
        if command == "/demo":
            if self.agent is None:
                self.write("error: /demo requires an initialized DeepSeek agent")
                return True
            self.write(self.agent.run("请运行实验二 BYOA 交互式演示，读取课程要求、检查交付状态、总结工具日志并给出报告建议。"))
            return True
        if self.agent is None:
            self.write("error: natural language chat requires DEEPSEEK_API_KEY")
            return True
        self.write(self.agent.run(command))
        return True


def run_chat(session: ChatSession) -> None:
    print("BYOA Course Agent")
    print(render_help())
    while True:
        try:
            line = input("\nyou > ")
        except EOFError:
            print()
            return
        if not session.handle_line(line):
            return
```

- [ ] **Step 5: Add `chat`, `check`, and `report` CLI commands**

In `build_parser`, add:

```python
subcommands.add_parser("chat", help="Start the interactive BYOA agent shell")
subcommands.add_parser("check", help="Check BYOA submission readiness")
subcommands.add_parser("report", help="Generate report materials without calling DeepSeek")
```

In `main`, handle deterministic commands before API config:

```python
if args.command == "check":
    tools = CourseAgentTools(DEFAULT_WORKSPACE, project_root=PROJECT_ROOT)
    print(render_check_result(tools.check_submission_readiness({})))
    return 0
if args.command == "report":
    tools = CourseAgentTools(DEFAULT_WORKSPACE, project_root=PROJECT_ROOT)
    material = generate_report_materials(PROJECT_ROOT, tools)
    report_path = save_report_draft(PROJECT_ROOT, material)
    print(material)
    print(f"\n[report draft] {report_path}")
    return 0
```

Import:

```python
from .chat import ChatSession, render_check_result, run_chat
from .reporting import generate_report_materials, save_report_draft
from .tools import CourseAgentTools, create_tool_schemas
```

For `chat`, initialize the agent with an observer:

```python
def print_tool_call(name: str, arguments: dict) -> None:
    print(f"tool > {name}({json.dumps(arguments, ensure_ascii=False)})")
```

Pass `tool_observer=print_tool_call` to `CourseAgent`, then call:

```python
if args.command == "chat":
    session = ChatSession(agent, agent.tools, PROJECT_ROOT)
    run_chat(session)
    return 0
```

- [ ] **Step 6: Add CLI tests**

In `tests/test_cli_and_deepseek.py`, add:

```python
def test_check_command_runs_without_api_key(self):
    result = subprocess.run(
        [sys.executable, "-m", "byoa_agent", "check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn("BYOA Submission Check", result.stdout)

def test_report_command_runs_without_api_key(self):
    result = subprocess.run(
        [sys.executable, "-m", "byoa_agent", "report"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn("Agent 简介", result.stdout)
```

- [ ] **Step 7: Run tests**

Run:

```bash
python -m unittest tests.test_chat
python -m unittest tests.test_cli_and_deepseek
python -m unittest discover -s tests
```

Expected: `OK`.

- [ ] **Step 8: Commit**

```bash
git add src/byoa_agent/agent.py src/byoa_agent/chat.py src/byoa_agent/cli.py tests/test_chat.py tests/test_cli_and_deepseek.py
git commit -m "feat: add interactive BYOA chat shell"
```

## Task 4: Generate Report Materials

**Files:**
- Modify: `src/byoa_agent/reporting.py`
- Modify: `reports/experiment2-draft.md`
- Modify: `tests/test_cli_and_deepseek.py`

- [ ] **Step 1: Add report material tests**

In `tests/test_cli_and_deepseek.py`, add:

```python
def test_report_materials_include_required_template_sections(self):
    from byoa_agent.reporting import generate_report_materials
    from byoa_agent.tools import CourseAgentTools

    text = generate_report_materials(ROOT, CourseAgentTools(ROOT.parent, project_root=ROOT))

    self.assertIn("Agent 简介", text)
    self.assertIn("运行说明", text)
    self.assertIn("AI 使用反思", text)
    self.assertIn("截图建议", text)
    self.assertIn("DeepSeek Function Calling", text)
```

- [ ] **Step 2: Run report test and verify failure**

Run:

```bash
python -m unittest tests.test_cli_and_deepseek.ReportingTests
```

Expected: missing `generate_report_materials`.

- [ ] **Step 3: Implement `generate_report_materials`**

In `src/byoa_agent/reporting.py`, add:

```python
def generate_report_materials(project_root: Path, tools: CourseAgentTools) -> str:
    readiness = json.loads(tools.check_submission_readiness({}))
    log_summary = json.loads(tools.summarize_tool_log({"path": "runs/latest.jsonl", "limit": 8}))
    tool_count = len(create_tool_schemas())
    pass_count = readiness["summary"]["pass"]
    total_count = readiness["summary"]["total"]
    log_calls = log_summary["summary"]["total_calls"]
    return f"""# Experiment 2 BYOA Report Draft

## 1. 基本信息

- 姓名：于重阳
- 学号：2024211429
- GitHub Repo：https://github.com/RollandXD/byoa-course-agent

## 2. Agent 简介

本项目实现了一个面向“软件产品综合研发实践”实验二的交互式 BYOA 课程助手。它采用命令行终端作为交互界面，用户可以通过 `python -m byoa_agent chat` 进入类似 Claude Code / Codex CLI 的连续对话环境，也可以使用 `/tools`、`/check`、`/report`、`/demo` 等固定命令获取稳定输出。Agent 的大模型部分使用 DeepSeek OpenAI-compatible Function Calling，本地工具负责读取课程 PPT、实验报告模板、项目仓库文件和 JSONL 工具调用日志。当前项目暴露 {tool_count} 个工具，超过实验要求的至少 2 个工具，并通过自检工具把 README、prompt、source code、tests、报告草稿和运行日志等交付证据串联起来。

## 3. 运行说明

运行前在 `.env` 中配置 `DEEPSEEK_API_KEY`。常用命令包括：`python -m byoa_agent tools` 查看工具 schema，`python -m byoa_agent chat` 启动交互式 agent shell，`python -m byoa_agent check` 检查交付状态，`python -m byoa_agent report` 生成报告材料，`python -m byoa_agent demo` 运行固定演示流程。运行过程中，Agent 会根据问题选择调用 `extract_pptx_text`、`extract_docx_text`、`check_submission_readiness`、`summarize_tool_log` 等工具，并将工具调用写入 `runs/latest.jsonl`。当前自检结果为 {pass_count}/{total_count} 项通过，最近工具日志包含 {log_calls} 次调用。

## 4. 截图建议

1. `python -m byoa_agent chat` 后输入 `/tools`，展示交互式界面和 Function Calling 工具 schema。
2. 在 chat 中提问“实验二要交什么”，展示 `extract_pptx_text` 读取 `Week 13-15.pptx` 的工具调用。
3. 输入 `/check`，展示 PASS/WARN/FAIL 自检结果，证明项目按 rubric 检查交付完整性。
4. 输入 `/report` 或查看 `runs/latest.jsonl`，展示工具日志摘要和报告材料生成过程。

## 5. AI 使用反思

本实验中，我使用 AI 辅助搭建 DeepSeek Function Calling 请求、工具 schema、CLI 入口、测试用例和报告材料。过程中遇到的主要问题不是“代码写不出来”，而是 AI 容易根据旧上下文做错误假设：例如早期测试默认实验一报告 DOCX 位于当前实验二目录，但实际课程文件已经拆到 `lab/01` 和 `lab/02`；AI 也曾倾向于提到项目并未使用的 Pydantic、pytest 或不存在的命令。为了解决这些问题，我把 agent 约束为先读取真实项目文件和课程资料，再回答实验要求；同时加入路径白名单、项目自检工具、JSONL 日志摘要和 unittest 验证。这样最终报告中的结论来自真实仓库状态和工具调用证据，而不是模型凭空补全。
"""
```

Also import:

```python
import json
from .tools import CourseAgentTools, create_tool_schemas
```

- [ ] **Step 4: Generate draft**

Run:

```bash
python -m byoa_agent report
```

Expected: terminal output includes `Agent 简介`, and `reports/experiment2-draft.md` is updated.

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest discover -s tests
```

Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add src/byoa_agent/reporting.py reports/experiment2-draft.md tests/test_cli_and_deepseek.py
git commit -m "feat: generate BYOA report materials"
```

## Task 5: Update Prompts and README

**Files:**
- Modify: `prompts/system.md`
- Modify: `prompts/demo.md`
- Modify: `README.md`

- [ ] **Step 1: Update system prompt**

Ensure `prompts/system.md` states:

```text
The implemented project has at least seven tools: list_workspace_files, list_project_files, extract_pptx_text, extract_docx_text, search_extracted_context, check_submission_readiness, and summarize_tool_log.
The supported commands are python -m byoa_agent tools, python -m byoa_agent chat, python -m byoa_agent check, python -m byoa_agent report, python -m byoa_agent demo, and python -m byoa_agent ask "<prompt>".
Do not claim this project uses a web UI. The main interaction interface is an interactive terminal shell.
```

- [ ] **Step 2: Update demo prompt**

Ensure `prompts/demo.md` asks the model to:

```text
1. List available PPTX and DOCX files.
2. List project files and verify README, prompts, source, tests, report draft, and run logs.
3. Read Week 13-15.pptx and identify Experiment 2 requirements.
4. Run the submission readiness check.
5. Summarize the latest tool log if present.
6. Produce a concise 95+ scoring-oriented report checklist and screenshot plan.
```

- [ ] **Step 3: Update README commands**

Document:

```bash
python -m byoa_agent chat
python -m byoa_agent check
python -m byoa_agent report
python -m byoa_agent demo
python -m byoa_agent ask "请根据课件总结实验二交付物和评分点"
```

Describe the project as an interactive terminal BYOA course assistant, not only a one-shot CLI.

- [ ] **Step 4: Run documentation-facing commands**

Run:

```bash
python -m byoa_agent tools
python -m byoa_agent check
python -m byoa_agent report
```

Expected: all commands exit with status 0.

- [ ] **Step 5: Commit**

```bash
git add README.md prompts/system.md prompts/demo.md
git commit -m "docs: document interactive BYOA agent workflow"
```

## Task 6: Final Verification, GitHub Push, and Submission Notes

**Files:**
- No planned source edits.
- Possible generated file: `runs/latest.jsonl`

- [ ] **Step 1: Run full tests**

Run:

```bash
python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Run no-key commands**

Run:

```bash
python -m byoa_agent tools
python -m byoa_agent check
python -m byoa_agent report
```

Expected: all commands exit with status 0 and produce report-friendly output.

- [ ] **Step 3: Run API-backed demo if `.env` exists**

Run:

```bash
python -m byoa_agent demo
```

Expected if `.env` has a real key: terminal output, refreshed `runs/latest.jsonl`, and refreshed `reports/experiment2-draft.md`.

Expected if no key exists: clear `DEEPSEEK_API_KEY` error. Do not fake a successful API demo.

- [ ] **Step 4: Inspect git status**

Run:

```bash
git status --short
```

Expected: only intentional generated files are modified.

- [ ] **Step 5: Commit final generated report/log if appropriate**

If `reports/experiment2-draft.md` changed:

```bash
git add reports/experiment2-draft.md
git commit -m "docs: refresh experiment two report draft"
```

If `runs/latest.jsonl` is intentionally kept ignored, do not force-add it unless the README says it is part of the submission evidence.

- [ ] **Step 6: Confirm remote**

Run:

```bash
git remote -v
```

Expected: a GitHub remote for `RollandXD/byoa-course-agent` or another user-approved repo.

- [ ] **Step 7: Push**

Run:

```bash
git push
```

Expected: all commits pushed to the configured branch.

If no remote exists, create the GitHub repo with:

```bash
gh repo create RollandXD/byoa-course-agent --public --source=. --remote=origin --push
```

Use the existing logged-in `gh` account and do not push secrets.

## Self-Review

- Spec coverage: The plan covers chat shell, self-check, log summary, report generation, test repair, docs, final verification, commits, and push.
- Placeholder scan: No task uses incomplete placeholder language.
- Type consistency: New methods use `CourseAgentTools`, `Path`, JSON strings, existing `save_report_draft`, and unittest-based tests to match the current codebase.
- Scope check: Web UI and DOCX automatic formatting remain out of scope, matching the design spec.
