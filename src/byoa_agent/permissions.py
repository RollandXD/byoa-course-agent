from __future__ import annotations

from typing import Callable


Prompter = Callable[[str], str]

MUTATING_TOOLS = {"write_file", "edit_file", "run_command"}


class PermissionGate:
    """Gate mutating tool calls behind user approval, like Claude Code permissions.

    Modes:
    - ``ask``: ask the prompter before each mutating call; without a prompter the
      call is denied so non-interactive runs stay read-only by default.
    - ``auto``: approve everything (the ``--yes`` / ``/auto`` escape hatch).
    """

    def __init__(self, mode: str = "ask", prompter: Prompter | None = None) -> None:
        if mode not in {"ask", "auto"}:
            raise ValueError(f"unknown permission mode: {mode}")
        self.mode = mode
        self.prompter = prompter

    def request(self, tool_name: str, summary: str) -> bool:
        if tool_name not in MUTATING_TOOLS:
            return True
        if self.mode == "auto":
            return True
        if self.prompter is None:
            return False
        answer = self.prompter(f"{tool_name}: {summary}").strip().lower()
        if answer in {"a", "always"}:
            self.mode = "auto"
            return True
        return answer in {"y", "yes"}
