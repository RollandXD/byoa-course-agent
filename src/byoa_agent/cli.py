from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import DEMO_PROMPT, SYSTEM_PROMPT, CourseAgent, default_run_log_path, read_prompt_file
from .config import AgentConfig, ConfigError
from .deepseek import DeepSeekError
from .reporting import save_report_draft
from .tools import create_tool_schemas


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE = PROJECT_ROOT.parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DeepSeek BYOA course task agent")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ask = subcommands.add_parser("ask", help="Ask the agent a question")
    ask.add_argument("prompt", help="Question or task for the agent")

    subcommands.add_parser("demo", help="Run the fixed experiment demo")
    subcommands.add_parser("tools", help="Print OpenAI-compatible tool schemas")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "tools":
        print(json.dumps(create_tool_schemas(), ensure_ascii=False, indent=2))
        return 0

    try:
        config = AgentConfig.from_env(DEFAULT_WORKSPACE)
        log_path = default_run_log_path(PROJECT_ROOT)
        if log_path.exists():
            log_path.unlink()
        system_prompt = read_prompt_file(PROJECT_ROOT / "prompts" / "system.md", SYSTEM_PROMPT)
        demo_prompt = read_prompt_file(PROJECT_ROOT / "prompts" / "demo.md", DEMO_PROMPT)
        agent = CourseAgent(
            config,
            log_path=log_path,
            system_prompt=system_prompt,
            project_root=PROJECT_ROOT,
        )
        prompt = demo_prompt if args.command == "demo" else args.prompt
        output = agent.run(prompt)
        report_path = save_report_draft(PROJECT_ROOT, output)
        print(output)
        print(f"\n[tool log] {log_path}")
        print(f"[report draft] {report_path}")
        return 0
    except (ConfigError, DeepSeekError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
