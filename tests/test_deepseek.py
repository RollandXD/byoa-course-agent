import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.config import AgentConfig, ConfigError
from byoa_agent.deepseek import DeepSeekClient, DeepSeekError


def sse(payload: dict) -> str:
    return "data: " + json.dumps(payload) + "\n"


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


class DeepSeekStreamingTests(unittest.TestCase):
    def make_client(self, lines):
        captured = {}

        def fake_stream(url, headers, body):
            captured["body"] = body
            return iter(lines)

        client = DeepSeekClient(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            stream_transport=fake_stream,
        )
        return client, captured

    def test_stream_emits_text_deltas_and_sets_stream_flag(self):
        client, captured = self.make_client(
            [
                sse({"choices": [{"delta": {"content": "你"}}]}),
                sse({"choices": [{"delta": {"content": "好"}}]}),
                "data: [DONE]\n",
            ]
        )
        chunks = []

        message = client.chat_stream([{"role": "user", "content": "hi"}], [], chunks.append)

        self.assertEqual(chunks, ["你", "好"])
        self.assertEqual(message["content"], "你好")
        self.assertTrue(captured["body"]["stream"])

    def test_stream_reassembles_tool_call_argument_fragments(self):
        client, _captured = self.make_client(
            [
                sse(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "id": "call_1",
                                            "function": {"name": "read_file", "arguments": '{"pa'},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ),
                sse(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {"index": 0, "function": {"arguments": 'th": "README.md"}'}}
                                    ]
                                }
                            }
                        ]
                    }
                ),
                "data: [DONE]\n",
            ]
        )

        message = client.chat_stream([{"role": "user", "content": "read"}], [], lambda _t: None)

        call = message["tool_calls"][0]
        self.assertEqual(call["id"], "call_1")
        self.assertEqual(call["function"]["name"], "read_file")
        self.assertEqual(json.loads(call["function"]["arguments"]), {"path": "README.md"})

    def test_stream_error_chunk_raises_deepseek_error(self):
        client, _captured = self.make_client([sse({"error": {"message": "quota exceeded"}})])

        with self.assertRaisesRegex(DeepSeekError, "quota"):
            client.chat_stream([{"role": "user", "content": "hi"}], [], lambda _t: None)

    def test_stream_ignores_keepalive_and_non_data_lines(self):
        client, _captured = self.make_client(
            [
                ": keep-alive\n",
                "\n",
                sse({"choices": [{"delta": {"content": "ok"}}]}),
                "data: [DONE]\n",
            ]
        )

        message = client.chat_stream([{"role": "user", "content": "hi"}], [], lambda _t: None)

        self.assertEqual(message["content"], "ok")


if __name__ == "__main__":
    unittest.main()
