import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.permissions import PermissionGate
from byoa_agent.tools import AgentToolbox, ToolError, create_tool_schemas


from support import find_course_root

COURSE_ROOT = find_course_root(ROOT)


def make_toolbox(**kwargs) -> AgentToolbox:
    kwargs.setdefault("project_root", ROOT)
    return AgentToolbox(COURSE_ROOT, **kwargs)


class ToolSchemaTests(unittest.TestCase):
    def test_tool_schemas_expose_general_and_course_skills(self):
        schemas = create_tool_schemas()
        names = [schema["function"]["name"] for schema in schemas]

        for general in ["read_file", "write_file", "edit_file", "list_files", "grep_files", "run_command"]:
            self.assertIn(general, names)
        for course in [
            "extract_pptx_text",
            "extract_docx_text",
            "search_extracted_context",
            "check_submission_readiness",
            "summarize_tool_log",
        ]:
            self.assertIn(course, names)
        self.assertGreaterEqual(len(names), 11)
        for schema in schemas:
            self.assertEqual(schema["type"], "function")
            self.assertIn("description", schema["function"])
            self.assertIn("parameters", schema["function"])


class GeneralToolTests(unittest.TestCase):
    def test_read_file_returns_repository_text(self):
        toolbox = make_toolbox()

        payload = json.loads(toolbox.read_file({"path": "byoa-course-agent/README.md"}))

        self.assertIn("BYOA", payload["content"])
        self.assertGreater(payload["total_lines"], 5)

    def test_read_file_rejects_binary_course_files(self):
        toolbox = make_toolbox()

        with self.assertRaisesRegex(ToolError, "extract_pptx_text"):
            toolbox.read_file({"path": "Week 13-15.pptx"})

    def test_read_file_rejects_paths_outside_workspace(self):
        toolbox = make_toolbox()

        with self.assertRaises(ToolError):
            toolbox.read_file({"path": "/etc/passwd"})

    def test_list_files_finds_course_and_project_files(self):
        toolbox = make_toolbox()

        payload = json.loads(toolbox.list_files({"pattern": "*.pptx"}))
        paths = {item["path"] for item in payload["files"]}

        self.assertIn("Week 13-15.pptx", paths)

    def test_grep_files_finds_lines_matching_regex(self):
        toolbox = make_toolbox()

        payload = json.loads(
            toolbox.grep_files({"pattern": "Claude Code", "glob": "*.md", "limit": 5})
        )

        self.assertGreaterEqual(len(payload["matches"]), 1)
        self.assertIn("Claude Code", payload["matches"][0]["text"])

    def test_write_and_edit_file_modify_project_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            toolbox = AgentToolbox(COURSE_ROOT, project_root=project_root)

            toolbox.write_file({"path": "notes/draft.md", "content": "hello agent"})
            toolbox.edit_file(
                {"path": "notes/draft.md", "old_string": "hello", "new_string": "hi"}
            )

            self.assertEqual((project_root / "notes" / "draft.md").read_text(encoding="utf-8"), "hi agent")

    def test_edit_file_requires_unique_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            (project_root / "a.txt").write_text("dup dup", encoding="utf-8")
            toolbox = AgentToolbox(COURSE_ROOT, project_root=project_root)

            with self.assertRaisesRegex(ToolError, "2 locations"):
                toolbox.edit_file({"path": "a.txt", "old_string": "dup", "new_string": "x"})

    def test_write_file_rejects_paths_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = AgentToolbox(COURSE_ROOT, project_root=Path(tmp))

            with self.assertRaisesRegex(ToolError, "restricted"):
                toolbox.write_file({"path": "../escape.txt", "content": "no"})

    def test_run_command_executes_in_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = AgentToolbox(COURSE_ROOT, project_root=Path(tmp))

            payload = json.loads(toolbox.run_command({"command": "echo agent-ok"}))

            self.assertEqual(payload["exit_code"], 0)
            self.assertIn("agent-ok", payload["stdout"])


class PermissionTests(unittest.TestCase):
    def test_mutating_tools_are_denied_without_prompter(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = PermissionGate(mode="ask", prompter=None)
            toolbox = AgentToolbox(COURSE_ROOT, project_root=Path(tmp), permissions=gate)

            payload = json.loads(toolbox.write_file({"path": "x.txt", "content": "no"}))

            self.assertIn("denied", payload)
            self.assertFalse((Path(tmp) / "x.txt").exists())

    def test_always_answer_switches_gate_to_auto(self):
        answers = iter(["a"])
        gate = PermissionGate(mode="ask", prompter=lambda _summary: next(answers))
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = AgentToolbox(COURSE_ROOT, project_root=Path(tmp), permissions=gate)

            toolbox.write_file({"path": "one.txt", "content": "1"})
            toolbox.write_file({"path": "two.txt", "content": "2"})

            self.assertEqual(gate.mode, "auto")
            self.assertTrue((Path(tmp) / "two.txt").exists())

    def test_read_only_tools_skip_the_gate(self):
        gate = PermissionGate(mode="ask", prompter=None)
        toolbox = make_toolbox(permissions=gate)

        payload = json.loads(toolbox.list_files({"pattern": "*.pptx"}))

        self.assertGreaterEqual(len(payload["files"]), 1)


class CourseToolTests(unittest.TestCase):
    def test_search_uses_previously_extracted_context(self):
        toolbox = make_toolbox()
        toolbox.extract_pptx_text({"path": "Week 13-15.pptx"})

        payload = json.loads(
            toolbox.search_extracted_context({"query": "Bring Your Own Agent", "limit": 3})
        )

        self.assertGreaterEqual(len(payload["matches"]), 1)
        self.assertIn("Bring Your Own Agent", payload["matches"][0]["text"])

    def test_extract_rejects_paths_outside_workspace(self):
        toolbox = make_toolbox()

        with self.assertRaises(ToolError):
            toolbox.extract_docx_text({"path": "/etc/passwd"})

    def test_submission_readiness_reports_project_evidence(self):
        toolbox = make_toolbox()

        payload = json.loads(toolbox.check_submission_readiness({}))
        checks = {item["id"]: item for item in payload["checks"]}

        self.assertEqual(payload["summary"]["total"], len(payload["checks"]))
        self.assertEqual(checks["readme"]["status"], "PASS")
        self.assertEqual(checks["prompts"]["status"], "PASS")
        self.assertEqual(checks["source"]["status"], "PASS")
        self.assertEqual(checks["tests"]["status"], "PASS")
        self.assertEqual(checks["tool_count"]["status"], "PASS")


class ToolLoggingTests(unittest.TestCase):
    def test_tool_calls_are_logged_as_json_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "run.jsonl"
            toolbox = make_toolbox(log_path=log_path)

            toolbox.list_files({"pattern": "*.pptx"})

            entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(entries[0]["tool"], "list_files")
            self.assertEqual(entries[0]["status"], "ok")
            self.assertIn("Week 13-15.pptx", entries[0]["result_preview"])

    def test_tool_log_summary_counts_jsonl_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            log_path = project_root / "latest.jsonl"
            log_path.write_text(
                "\n".join(
                    [
                        json.dumps({"tool": "list_files", "arguments": {"pattern": "*.pptx"}, "status": "ok"}),
                        json.dumps(
                            {
                                "tool": "extract_pptx_text",
                                "arguments": {"path": "Week 13-15.pptx"},
                                "status": "ok",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            toolbox = AgentToolbox(COURSE_ROOT, project_root=project_root, log_path=log_path)

            payload = json.loads(toolbox.summarize_tool_log({"path": "latest.jsonl", "limit": 5}))

            self.assertEqual(payload["summary"]["total_calls"], 2)
            self.assertIn("extract_pptx_text", payload["summary"]["tools_used"])
            self.assertEqual(payload["calls"][0]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
