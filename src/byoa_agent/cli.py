from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ui
from .agent import (
    DEMO_PROMPT,
    SYSTEM_PROMPT,
    build_session,
    default_run_log_path,
    read_prompt_file,
)
from .chat import ChatSession, render_check_result, run_chat
from .config import AgentConfig, ConfigError
from .deepseek import DeepSeekError
from .permissions import PermissionGate
from .reporting import generate_report_materials, save_report_draft
from .tools import AgentToolbox, create_tool_schemas


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE = PROJECT_ROOT.parent


class StreamRenderer:
    """Print streamed text and Claude Code style tool lines without overlap."""

    def __init__(self, color: bool) -> None:
        self.color = color
        self.midline = False

    def on_text(self, chunk: str) -> None:
        print(chunk, end="", flush=True)
        self.midline = not chunk.endswith("\n")

    def on_tool_call(self, name: str, arguments: dict) -> None:
        if self.midline:
            print()
            self.midline = False
        print(ui.tool_call_line(name, arguments, self.color))

    def on_tool_result(self, name: str, raw_result: str) -> None:
        print(ui.tool_result_line(raw_result, self.color))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="byoa_agent",
        description="BYOA Code: a Claude Code style DeepSeek course agent",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="auto-approve write/edit/shell tool calls (like a permissive mode)",
    )
    subcommands = parser.add_subparsers(dest="command")

    ask = subcommands.add_parser("ask", help="Ask the agent a single question")
    ask.add_argument("prompt", help="Question or task for the agent")

    subcommands.add_parser("chat", help="Start the interactive agent shell (default)")
    subcommands.add_parser("check", help="Check BYOA submission readiness")
    subcommands.add_parser("report", help="Generate report materials without calling DeepSeek")
    subcommands.add_parser("demo", help="Run the fixed experiment demo")
    subcommands.add_parser("tools", help="Print OpenAI-compatible tool schemas")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print("\nbye")
        return 0


def _main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command or "chat"
    if command == "tools":
        print(json.dumps(create_tool_schemas(), ensure_ascii=False, indent=2))
        return 0
    if command == "check":
        toolbox = AgentToolbox(DEFAULT_WORKSPACE, project_root=PROJECT_ROOT)
        print(render_check_result(toolbox.check_submission_readiness({})))
        return 0
    if command == "report":
        toolbox = AgentToolbox(DEFAULT_WORKSPACE, project_root=PROJECT_ROOT)
        output = generate_report_materials(PROJECT_ROOT, toolbox)
        report_path = save_report_draft(PROJECT_ROOT, output)
        print(output)
        print(f"\n[report draft] {report_path}")
        return 0

    color = ui.supports_color()
    renderer = StreamRenderer(color)
    interactive = sys.stdin.isatty()
    if args.yes:
        gate = PermissionGate(mode="auto")
    else:
        prompter = _make_prompter(color) if interactive else None
        gate = PermissionGate(mode="ask", prompter=prompter)

    try:
        config = AgentConfig.from_env(DEFAULT_WORKSPACE, env_file=PROJECT_ROOT / ".env")
    except ConfigError as exc:
        if command == "chat":
            toolbox = AgentToolbox(DEFAULT_WORKSPACE, project_root=PROJECT_ROOT, permissions=gate)
            session = ChatSession(None, toolbox, PROJECT_ROOT)
            banner = ui.banner("offline", str(DEFAULT_WORKSPACE), len(create_tool_schemas()), color)
            print(f"[offline] {exc}")
            run_chat(session, banner=banner)
            return 0
        print(f"error: {exc}", file=sys.stderr)
        return 1

    log_path = default_run_log_path(PROJECT_ROOT)
    if log_path.exists():
        log_path.unlink()
    system_prompt = read_prompt_file(PROJECT_ROOT / "prompts" / "system.md", SYSTEM_PROMPT)
    agent = build_session(
        config,
        PROJECT_ROOT,
        log_path=log_path,
        system_prompt=system_prompt,
        permissions=gate,
        on_text=renderer.on_text,
        on_tool_call=renderer.on_tool_call,
        on_tool_result=renderer.on_tool_result,
    )

    try:
        if command == "chat":
            session = ChatSession(agent, agent.toolbox, PROJECT_ROOT, stream_output=True)
            banner = ui.banner(config.model, str(config.workspace), len(create_tool_schemas()), color)
            run_chat(session, banner=banner)
            return 0
        demo_prompt = read_prompt_file(PROJECT_ROOT / "prompts" / "demo.md", DEMO_PROMPT)
        prompt = demo_prompt if command == "demo" else args.prompt
        agent.run_turn(prompt)
        print(f"\n\n[tool log] {log_path}")
        return 0
    except DeepSeekError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _make_prompter(color: bool):
    def prompter(summary: str) -> str:
        question = ui.paint(f"允许 {summary} ? [y/n/a(lways)] ", ui.YELLOW, color)
        try:
            return input(question)
        except EOFError:
            return "n"

    return prompter


if __name__ == "__main__":
    raise SystemExit(main())
