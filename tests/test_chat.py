import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.chat import ChatSession, render_check_result, render_help, run_chat
from byoa_agent.permissions import PermissionGate
from byoa_agent.tools import AgentToolbox


from support import find_course_root

COURSE_ROOT = find_course_root(ROOT)


class FakeAgent:
    def __init__(self):
        self.turns = []
        self.cleared = False

    def run_turn(self, user_input: str) -> str:
        self.turns.append(user_input)
        return f"回答: {user_input}"

    def clear(self) -> None:
        self.cleared = True

    def context_stats(self) -> dict:
        return {"messages": 3, "approx_chars": 120}


def make_session(agent=None, gate=None) -> ChatSession:
    toolbox = AgentToolbox(COURSE_ROOT, project_root=ROOT, permissions=gate)
    return ChatSession(agent=agent, tools=toolbox, project_root=ROOT, output=[])


class ChatRenderTests(unittest.TestCase):
    def test_help_mentions_core_commands(self):
        text = render_help()

        for command in ["/tools", "/check", "/report", "/clear", "/auto", "/exit"]:
            self.assertIn(command, text)

    def test_check_renderer_formats_status_lines(self):
        payload = {
            "summary": {"total": 1, "pass": 1, "warn": 0, "fail": 0},
            "checks": [
                {"id": "readme", "label": "README.md exists", "status": "PASS", "detail": "ok"}
            ],
        }

        text = render_check_result(json.dumps(payload, ensure_ascii=False))

        self.assertIn("[PASS] README.md exists", text)
        self.assertIn("1/1", text)


class ChatSessionTests(unittest.TestCase):
    def test_slash_tools_lists_general_and_course_tools(self):
        session = make_session()

        keep_running = session.handle_line("/tools")

        self.assertTrue(keep_running)
        output = "\n".join(session.output)
        self.assertIn("read_file", output)
        self.assertIn("extract_pptx_text", output)

    def test_slash_check_prints_readiness_without_network(self):
        session = make_session()

        keep_running = session.handle_line("/check")

        self.assertTrue(keep_running)
        self.assertIn("BYOA Submission Check", "\n".join(session.output))

    def test_slash_auto_toggles_permission_gate(self):
        gate = PermissionGate(mode="ask", prompter=None)
        session = make_session(gate=gate)

        session.handle_line("/auto")
        self.assertEqual(gate.mode, "auto")
        session.handle_line("/auto")
        self.assertEqual(gate.mode, "ask")

    def test_slash_clear_resets_agent_context(self):
        agent = FakeAgent()
        session = make_session(agent=agent)

        session.handle_line("/clear")

        self.assertTrue(agent.cleared)
        self.assertIn("已清空", "\n".join(session.output))

    def test_slash_context_reports_usage(self):
        session = make_session(agent=FakeAgent())

        session.handle_line("/context")

        self.assertIn("3 条消息", "\n".join(session.output))

    def test_natural_language_goes_through_agent_session(self):
        agent = FakeAgent()
        session = make_session(agent=agent)

        session.handle_line("实验二要交什么")

        self.assertEqual(agent.turns, ["实验二要交什么"])
        self.assertIn("回答: 实验二要交什么", "\n".join(session.output))

    def test_natural_language_without_agent_reports_offline(self):
        session = make_session(agent=None)

        session.handle_line("你好")

        self.assertIn("DEEPSEEK_API_KEY", "\n".join(session.output))

    def test_slash_exit_stops_loop(self):
        session = make_session()

        keep_running = session.handle_line("/exit")

        self.assertFalse(keep_running)

    def test_ctrl_c_exits_without_traceback(self):
        session = make_session()
        stream = io.StringIO()

        with patch("builtins.input", side_effect=KeyboardInterrupt), redirect_stdout(stream):
            run_chat(session)

        self.assertIn("bye", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
