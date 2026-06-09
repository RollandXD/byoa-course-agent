from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import unicodedata


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITALIC = "\x1b[3m"
UNDERLINE = "\x1b[4m"
CYAN = "\x1b[36m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
MAGENTA = "\x1b[35m"
BLUE = "\x1b[34m"


def supports_color(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR") is not None:
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def paint(text: str, code: str, enabled: bool = True) -> str:
    if not enabled or not code:
        return text
    return f"{code}{text}{RESET}"


def display_width(text: str) -> int:
    """Terminal cell width of a string, counting CJK characters as two cells."""
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


# ---------------------------------------------------------------------------
# banner


def banner(model: str, workspace: str, tool_count: int, color: bool = True, version: str = "0.3") -> str:
    rows = [
        ("✻ BYOA Code", f"v{version}"),
        ("model", model),
        ("tools", f"{tool_count} 个（6 通用编码 + 5 课程技能）"),
        ("workspace", _shorten(workspace, 46)),
    ]
    body_lines = [f"{label}  {value}" if label.startswith("✻") else f"  {label:<10} {value}" for label, value in rows]
    hint = "/help 查看命令 · @文件 引用 · !命令 直通 shell · Ctrl+C 中断"
    width = max(display_width(line) for line in body_lines + [hint]) + 2

    def pad(line: str) -> str:
        return line + " " * (width - display_width(line))

    border = paint("╭" + "─" * (width + 2) + "╮", MAGENTA, color)
    bottom = paint("╰" + "─" * (width + 2) + "╯", MAGENTA, color)
    edge = paint("│", MAGENTA, color)
    out = [border]
    for index, line in enumerate(body_lines):
        styled = pad(line)
        if index == 0:
            styled = paint(pad(line), BOLD, color)
        else:
            styled = paint(pad(line), DIM, color)
        out.append(f"{edge} {styled} {edge}")
    out.append(f"{edge} {paint(pad(hint), DIM, color)} {edge}")
    out.append(bottom)
    return "\n".join(out)


def _shorten(text: str, limit: int) -> str:
    if display_width(text) <= limit:
        return text
    return "…" + text[-(limit - 1) :]


# ---------------------------------------------------------------------------
# tool call lines


def summarize_arguments(arguments: dict, max_length: int = 80) -> str:
    parts = []
    for key, value in arguments.items():
        rendered = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        rendered = rendered.replace("\n", "⏎")
        if len(rendered) > 40:
            rendered = rendered[:37] + "..."
        parts.append(f"{key}={rendered}")
    text = ", ".join(parts)
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text


def tool_call_line(name: str, arguments: dict, color: bool = True) -> str:
    summary = summarize_arguments(arguments)
    return paint("⏺ ", GREEN, color) + paint(name, BOLD + CYAN, color) + paint(f"({summary})", CYAN, color)


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
            mark = "✓" if payload["exit_code"] == 0 else "✗"
            detail = f"{mark} exit {payload['exit_code']}"
        elif "summary" in payload and isinstance(payload["summary"], dict):
            summary = payload["summary"]
            if "pass" in summary:
                detail = f"{summary['pass']} PASS / {summary.get('warn', 0)} WARN / {summary.get('fail', 0)} FAIL"
            elif "total_calls" in summary:
                detail = f"{summary['total_calls']} 次工具调用"
        elif "text" in payload:
            detail = f"{len(str(payload['text']))} 字符"
        elif "bytes_written" in payload:
            detail = f"已写入 {payload['bytes_written']} 字节 → {payload.get('path', '')}"
        elif "replacements" in payload:
            detail = f"已替换 {payload['replacements']} 处 → {payload.get('path', '')}"
        elif "path" in payload:
            detail = str(payload["path"])
    return paint(f"  ⎿ {detail}", DIM, color)


# ---------------------------------------------------------------------------
# diff colouring (permission previews)


def colorize_diff(text: str, color: bool = True) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            lines.append(paint(line, BOLD, color))
        elif line.startswith("@@"):
            lines.append(paint(line, CYAN, color))
        elif line.startswith("+"):
            lines.append(paint(line, GREEN, color))
        elif line.startswith("-"):
            lines.append(paint(line, RED, color))
        else:
            lines.append(paint(line, DIM, color))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# streaming markdown rendering


_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BULLET = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_ORDERED = re.compile(r"^(\s*)(\d+)([.)])\s+(.*)$")
_HEADER = re.compile(r"^(#{1,6})\s+(.*)$")
_HRULE = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def style_inline(text: str, color: bool = True) -> str:
    """Apply inline markdown styling; markers are stripped even without color."""
    code_spans: list[str] = []

    def stash_code(match: re.Match) -> str:
        code_spans.append(match.group(1))
        return f"\x00{len(code_spans) - 1}\x00"

    text = _INLINE_CODE.sub(stash_code, text)
    text = _LINK.sub(lambda m: paint(m.group(1), UNDERLINE, color) + paint(f" ({m.group(2)})", DIM, color), text)
    text = _BOLD.sub(lambda m: paint(m.group(1), BOLD, color), text)
    text = _ITALIC.sub(lambda m: paint(m.group(1), ITALIC, color), text)
    for index, span in enumerate(code_spans):
        text = text.replace(f"\x00{index}\x00", paint(span, CYAN, color))
    return text


class MarkdownPrinter:
    """Render markdown to ANSI line by line, so streamed text styles as it arrives."""

    def __init__(self, color: bool = True, out=None) -> None:
        self.color = color
        self.out = out or sys.stdout
        self.buffer = ""
        self.in_code_block = False

    def feed(self, chunk: str) -> None:
        self.buffer += chunk
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self._emit(self.render_line(line))

    def flush(self) -> None:
        """Force out a partially streamed line (before a tool line interrupts it)."""
        if self.buffer:
            self._emit(self.render_line(self.buffer))
            self.buffer = ""

    def finish(self) -> None:
        self.flush()
        self.in_code_block = False

    @property
    def midline(self) -> bool:
        return bool(self.buffer)

    def _emit(self, text: str) -> None:
        print(text, file=self.out)

    def render_line(self, line: str) -> str:
        stripped = line.strip()
        if stripped.startswith("```"):
            language = stripped[3:].strip()
            if not self.in_code_block:
                self.in_code_block = True
                title = f"─── {language} " if language else "─── "
                return paint("  ╭" + title + "─" * max(4, 44 - display_width(title)), DIM, self.color)
            self.in_code_block = False
            return paint("  ╰" + "─" * 44, DIM, self.color)
        if self.in_code_block:
            return paint("  │ ", DIM, self.color) + line
        header = _HEADER.match(stripped)
        if header:
            level = len(header.group(1))
            text = style_inline(header.group(2), self.color)
            if level == 1:
                return paint("◆ ", MAGENTA, self.color) + paint(text, BOLD + MAGENTA, self.color)
            if level == 2:
                return paint("◇ ", CYAN, self.color) + paint(text, BOLD + CYAN, self.color)
            return paint(text, BOLD, self.color)
        if _HRULE.match(line):
            return paint("─" * 44, DIM, self.color)
        if stripped.startswith(">"):
            quoted = stripped.lstrip("> ")
            return paint("▌ ", DIM, self.color) + paint(style_inline(quoted, self.color), DIM, self.color)
        if stripped.startswith("|"):
            if _TABLE_SEP.match(stripped):
                return paint("  " + "─" * 40, DIM, self.color)
            cells = style_inline(stripped, self.color)
            return "  " + cells.replace("|", paint("│", DIM, self.color))
        bullet = _BULLET.match(line)
        if bullet:
            indent, _marker, rest = bullet.groups()
            return f"{indent}" + paint("• ", CYAN, self.color) + style_inline(rest, self.color)
        ordered = _ORDERED.match(line)
        if ordered:
            indent, number, dot, rest = ordered.groups()
            return f"{indent}" + paint(f"{number}{dot} ", CYAN, self.color) + style_inline(rest, self.color)
        return style_inline(line, self.color)


# ---------------------------------------------------------------------------
# spinner + per-turn display


class Spinner:
    FRAMES = "✻✼✽✾✿❀"

    def __init__(self, enabled: bool, label: str = "思考中", out=None) -> None:
        self.enabled = enabled
        self.label = label
        self.out = out or sys.stdout
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join()
        self._thread = None
        self.out.write("\r\x1b[2K")
        self.out.flush()

    def _spin(self) -> None:
        started = time.monotonic()
        index = 0
        while not self._stop.wait(0.12):
            frame = self.FRAMES[index % len(self.FRAMES)]
            elapsed = time.monotonic() - started
            self.out.write(f"\r\x1b[2K{DIM}{MAGENTA}{frame}{RESET}{DIM} {self.label}… ({elapsed:.1f}s){RESET}")
            self.out.flush()
            index += 1


class TurnDisplay:
    """Own one conversational turn's visuals: spinner, markdown stream, tool lines, stats."""

    def __init__(self, color: bool | None = None, out=None) -> None:
        self.out = out or sys.stdout
        self.color = supports_color(self.out) if color is None else color
        self.markdown = MarkdownPrinter(self.color, self.out)
        self.spinner = Spinner(enabled=self.color and hasattr(self.out, "isatty") and self.out.isatty(), out=self.out)
        self.tool_calls = 0
        self._started = 0.0

    def begin_turn(self) -> None:
        self.tool_calls = 0
        self._started = time.monotonic()
        self.spinner.start()

    def on_text(self, chunk: str) -> None:
        self.spinner.stop()
        self.markdown.feed(chunk)

    def on_tool_call(self, name: str, arguments: dict) -> None:
        self.spinner.stop()
        self.markdown.flush()
        print(tool_call_line(name, arguments, self.color), file=self.out)

    def on_tool_result(self, name: str, raw_result: str) -> None:
        print(tool_result_line(raw_result, self.color), file=self.out)
        self.tool_calls += 1
        self.spinner.start()

    def end_turn(self, context_stats: dict | None = None, interrupted: bool = False) -> None:
        self.spinner.stop()
        self.markdown.finish()
        duration = time.monotonic() - self._started
        parts = [f"⏱ {duration:.1f}s"]
        if self.tool_calls:
            parts.append(f"⚒ {self.tool_calls} 次工具调用")
        if context_stats and context_stats.get("max_chars"):
            percent = min(99, round(100 * context_stats["approx_chars"] / context_stats["max_chars"]))
            parts.append(f"◔ 上下文 {percent}%")
        if interrupted:
            parts.append("⨯ 已中断")
        print(paint("  " + " · ".join(parts), DIM, self.color), file=self.out)
