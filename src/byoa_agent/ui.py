from __future__ import annotations

import json
import os
import sys


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
CYAN = "\x1b[36m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
MAGENTA = "\x1b[35m"


def supports_color(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") is not None:
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def paint(text: str, code: str, enabled: bool = True) -> str:
    if not enabled or not code:
        return text
    return f"{code}{text}{RESET}"


def summarize_arguments(arguments: dict, max_length: int = 80) -> str:
    parts = []
    for key, value in arguments.items():
        rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        if len(rendered) > 40:
            rendered = rendered[:37] + "..."
        parts.append(f"{key}={rendered}")
    text = ", ".join(parts)
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text


def tool_call_line(name: str, arguments: dict, color: bool = True) -> str:
    summary = summarize_arguments(arguments)
    return paint(f"⏺ {name}({summary})", CYAN, color)


def tool_result_line(raw_result: str, color: bool = True) -> str:
    """Render a one-line summary of a JSON tool result, Claude Code style."""
    try:
        payload = json.loads(raw_result)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict) and payload.get("error"):
        return paint(f"  ⎿ 错误: {payload['error']}", RED, color)
    if isinstance(payload, dict) and payload.get("denied"):
        return paint(f"  ⎿ 已拒绝: {payload['denied']}", YELLOW, color)
    detail = f"{len(raw_result)} 字符"
    if isinstance(payload, dict):
        if "files" in payload:
            detail = f"{len(payload['files'])} 个文件"
        elif "matches" in payload:
            detail = f"{len(payload['matches'])} 处匹配"
        elif "content" in payload:
            detail = f"{len(str(payload['content']))} 字符" + ("（已截断）" if payload.get("truncated") else "")
        elif "exit_code" in payload:
            detail = f"exit {payload['exit_code']}"
        elif "summary" in payload and isinstance(payload["summary"], dict):
            summary = payload["summary"]
            if "pass" in summary:
                detail = f"{summary['pass']} PASS / {summary.get('warn', 0)} WARN / {summary.get('fail', 0)} FAIL"
            elif "total_calls" in summary:
                detail = f"{summary['total_calls']} 次工具调用"
        elif "text" in payload:
            detail = f"{len(str(payload['text']))} 字符"
        elif "path" in payload:
            detail = str(payload["path"])
    return paint(f"  ⎿ {detail}", DIM, color)


def banner(model: str, workspace: str, tool_count: int, color: bool = True) -> str:
    title = paint("✻ BYOA Code", BOLD + MAGENTA, color) + paint(
        " — Claude Code 风格的 DeepSeek 课程智能体", BOLD, color
    )
    info = paint(
        f"  model: {model} · tools: {tool_count} · workspace: {workspace}", DIM, color
    )
    hint = paint("  /help 查看命令 · 自然语言直接对话 · Ctrl+C 退出", DIM, color)
    return "\n".join([title, info, hint])
