import json
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.chat import ChatSession, render_check_result, render_help, run_chat
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
            "checks": [
                {
                    "id": "readme",
                    "label": "README.md exists",
                    "status": "PASS",
                    "detail": "ok",
                }
            ],
        }

        text = render_check_result(json.dumps(payload, ensure_ascii=False))

        self.assertIn("[PASS] README.md exists", text)
        self.assertIn("1/1", text)


class ChatSessionTests(unittest.TestCase):
    def test_slash_tools_prints_schema_without_network(self):
        session = ChatSession(
            agent=None,
            tools=CourseAgentTools(COURSE_ROOT, project_root=ROOT),
            project_root=ROOT,
            output=[],
        )

        keep_running = session.handle_line("/tools")

        self.assertTrue(keep_running)
        self.assertIn("list_workspace_files", "\n".join(session.output))

    def test_slash_check_prints_readiness_without_network(self):
        session = ChatSession(
            agent=None,
            tools=CourseAgentTools(COURSE_ROOT, project_root=ROOT),
            project_root=ROOT,
            output=[],
        )

        keep_running = session.handle_line("/check")

        self.assertTrue(keep_running)
        self.assertIn("BYOA Submission Check", "\n".join(session.output))

    def test_slash_exit_stops_loop(self):
        session = ChatSession(
            agent=None,
            tools=CourseAgentTools(COURSE_ROOT, project_root=ROOT),
            project_root=ROOT,
            output=[],
        )

        keep_running = session.handle_line("/exit")

        self.assertFalse(keep_running)

    def test_ctrl_c_exits_without_traceback(self):
        session = ChatSession(
            agent=None,
            tools=CourseAgentTools(COURSE_ROOT, project_root=ROOT),
            project_root=ROOT,
            output=[],
        )
        stream = io.StringIO()

        with patch("builtins.input", side_effect=KeyboardInterrupt), redirect_stdout(stream):
            run_chat(session)

        self.assertIn("bye", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
