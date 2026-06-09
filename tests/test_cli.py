import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.reporting import save_report_draft


class CliSmokeTests(unittest.TestCase):
    def test_tools_command_prints_all_schemas(self):
        result = subprocess.run(
            [sys.executable, "-m", "byoa_agent", "tools"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("read_file", result.stdout)
        self.assertIn("run_command", result.stdout)
        self.assertIn("extract_pptx_text", result.stdout)

    def test_check_command_runs_without_api_key(self):
        env = os.environ.copy()
        env["DEEPSEEK_API_KEY"] = ""

        result = subprocess.run(
            [sys.executable, "-m", "byoa_agent", "check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BYOA Submission Check", result.stdout)

    def test_default_command_is_chat_and_works_offline(self):
        env = os.environ.copy()
        env["DEEPSEEK_API_KEY"] = ""

        result = subprocess.run(
            [sys.executable, "-m", "byoa_agent"],
            cwd=ROOT,
            input="/help\n/exit\n",
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BYOA Code", result.stdout)
        self.assertIn("/tools", result.stdout)

    def test_main_handles_keyboard_interrupt_without_traceback(self):
        from byoa_agent import cli

        stream = io.StringIO()
        with patch("byoa_agent.cli.create_tool_schemas", side_effect=KeyboardInterrupt):
            with redirect_stdout(stream):
                code = cli.main(["tools"])

        self.assertEqual(code, 0)
        self.assertIn("bye", stream.getvalue())

    def test_report_command_runs_without_api_key(self):
        env = os.environ.copy()
        env["DEEPSEEK_API_KEY"] = ""
        draft_path = ROOT / "reports" / "experiment2-draft.md"
        original_draft = draft_path.read_text(encoding="utf-8") if draft_path.exists() else None

        try:
            result = subprocess.run(
                [sys.executable, "-m", "byoa_agent", "report"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Agent 简介", result.stdout)
        finally:
            # the command saves the draft as a side effect; keep the committed copy
            if original_draft is not None:
                draft_path.write_text(original_draft, encoding="utf-8")


class ReportingTests(unittest.TestCase):
    def test_report_draft_is_saved_with_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_report_draft(Path(tmp), "Requirement summary\n- Tool use")

            text = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "experiment2-draft.md")
            self.assertIn("# Experiment 2 BYOA Report Draft", text)
            self.assertIn("Requirement summary", text)

    def test_report_materials_include_required_template_sections(self):
        from byoa_agent.reporting import generate_report_materials
        from byoa_agent.tools import AgentToolbox

        text = generate_report_materials(ROOT, AgentToolbox(ROOT.parent, project_root=ROOT))

        self.assertIn("Agent 简介", text)
        self.assertIn("运行说明", text)
        self.assertIn("AI 使用反思", text)
        self.assertIn("截图建议", text)
        self.assertIn("DeepSeek Function Calling", text)
        self.assertIn("Claude Code", text)


if __name__ == "__main__":
    unittest.main()
