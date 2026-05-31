import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.tools import (
    CourseAgentTools,
    ToolError,
    create_tool_schemas,
)


COURSE_ROOT = ROOT.parent


class ToolSchemaTests(unittest.TestCase):
    def test_tool_schemas_expose_at_least_four_distinct_skills(self):
        schemas = create_tool_schemas()
        names = [schema["function"]["name"] for schema in schemas]

        self.assertGreaterEqual(len(names), 4)
        self.assertIn("list_workspace_files", names)
        self.assertIn("extract_pptx_text", names)
        self.assertIn("extract_docx_text", names)
        self.assertIn("search_extracted_context", names)
        self.assertIn("list_project_files", names)
        for schema in schemas:
            self.assertEqual(schema["type"], "function")
            self.assertIn("description", schema["function"])
            self.assertIn("parameters", schema["function"])

    def test_project_files_tool_lists_repository_artifacts(self):
        tools = CourseAgentTools(COURSE_ROOT, project_root=ROOT)

        result = tools.list_project_files({"max_depth": 3})
        payload = json.loads(result)
        paths = {item["path"] for item in payload["files"]}

        self.assertIn("README.md", paths)
        self.assertIn("prompts/system.md", paths)
        self.assertIn("src/byoa_agent/tools.py", paths)

    def test_tools_reject_paths_outside_workspace(self):
        tools = CourseAgentTools(COURSE_ROOT)

        with self.assertRaises(ToolError):
            tools.extract_docx_text({"path": "/etc/passwd"})

    def test_search_uses_previously_extracted_context(self):
        tools = CourseAgentTools(COURSE_ROOT)
        tools.extract_pptx_text({"path": "Week 13-15.pptx"})

        result = tools.search_extracted_context({"query": "Bring Your Own Agent", "limit": 3})
        payload = json.loads(result)

        self.assertGreaterEqual(len(payload["matches"]), 1)
        self.assertIn("Bring Your Own Agent", payload["matches"][0]["text"])


class ToolLoggingTests(unittest.TestCase):
    def test_tool_calls_are_logged_as_json_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "run.jsonl"
            tools = CourseAgentTools(COURSE_ROOT, log_path=log_path)

            tools.list_workspace_files({"pattern": "*.pptx"})

            entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(entries[0]["tool"], "list_workspace_files")
            self.assertEqual(entries[0]["status"], "ok")
            self.assertIn("Week 13-15.pptx", entries[0]["result_preview"])


if __name__ == "__main__":
    unittest.main()
