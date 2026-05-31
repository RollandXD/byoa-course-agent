import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.config import AgentConfig, ConfigError
from byoa_agent.deepseek import DeepSeekClient, DeepSeekError
from byoa_agent.reporting import save_report_draft


class ConfigTests(unittest.TestCase):
    def test_missing_deepseek_key_raises_clear_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ConfigError, "DEEPSEEK_API_KEY"):
                AgentConfig.from_env(ROOT.parent)

    def test_config_defaults_to_current_deepseek_model(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=True):
            config = AgentConfig.from_env(ROOT.parent)

        self.assertEqual(config.base_url, "https://api.deepseek.com")
        self.assertEqual(config.model, "deepseek-v4-flash")

    def test_config_can_load_key_from_dotenv_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("DEEPSEEK_API_KEY=file-key\nDEEPSEEK_MODEL=custom-model\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                config = AgentConfig.from_env(ROOT.parent, env_file=env_file)

        self.assertEqual(config.api_key, "file-key")
        self.assertEqual(config.model, "custom-model")


class DeepSeekClientTests(unittest.TestCase):
    def test_client_builds_openai_compatible_tool_request(self):
        captured = {}

        def fake_transport(url, headers, body):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = body
            return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}

        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            transport=fake_transport,
        )
        message = client.chat(
            messages=[{"role": "user", "content": "hello"}],
            tools=[{"type": "function", "function": {"name": "noop", "parameters": {"type": "object"}}}],
        )

        self.assertEqual(message["content"], "ok")
        self.assertEqual(captured["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(captured["body"]["model"], "deepseek-v4-flash")
        self.assertIn("tools", captured["body"])

    def test_client_rejects_malformed_response(self):
        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            transport=lambda _url, _headers, _body: {"choices": []},
        )

        with self.assertRaises(DeepSeekError):
            client.chat(messages=[{"role": "user", "content": "hello"}], tools=[])


class CliSmokeTests(unittest.TestCase):
    def test_tools_command_runs_from_project_root(self):
        result = subprocess.run(
            [sys.executable, "-m", "byoa_agent", "tools"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("list_workspace_files", result.stdout)


class ReportingTests(unittest.TestCase):
    def test_report_draft_is_saved_with_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_report_draft(Path(tmp), "Requirement summary\n- Tool use")

            text = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "experiment2-draft.md")
            self.assertIn("# Experiment 2 BYOA Report Draft", text)
            self.assertIn("Requirement summary", text)


if __name__ == "__main__":
    unittest.main()
