import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.agent import COMPACTION_NOTE, AgentSession
from byoa_agent.tools import AgentToolbox


from support import find_course_root

COURSE_ROOT = find_course_root(ROOT)


class FakeClient:
    """Replays scripted assistant messages and records every request."""

    def __init__(self, scripted_messages):
        self.scripted = list(scripted_messages)
        self.requests = []

    def chat(self, messages, tools):
        self.requests.append([dict(message) for message in messages])
        return self.scripted.pop(0)

    def chat_stream(self, messages, tools, on_text):
        message = self.chat(messages, tools)
        if message.get("content"):
            on_text(message["content"])
        return message


def tool_call(name: str, arguments: dict, call_id: str = "call_1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


class AgentSessionTests(unittest.TestCase):
    def test_session_keeps_history_across_turns(self):
        client = FakeClient(
            [
                {"role": "assistant", "content": "第一轮回答"},
                {"role": "assistant", "content": "第二轮回答"},
            ]
        )
        session = AgentSession(client, AgentToolbox(COURSE_ROOT, project_root=ROOT), stream=False)

        session.run_turn("第一个问题")
        session.run_turn("第二个问题")

        second_request = client.requests[1]
        contents = [message.get("content") for message in second_request]
        self.assertIn("第一个问题", contents)
        self.assertIn("第一轮回答", contents)
        self.assertIn("第二个问题", contents)

    def test_tool_calls_are_dispatched_and_fed_back(self):
        client = FakeClient(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_call("list_files", {"pattern": "*.pptx"})],
                },
                {"role": "assistant", "content": "课件已找到"},
            ]
        )
        observed = []
        session = AgentSession(
            client,
            AgentToolbox(COURSE_ROOT, project_root=ROOT),
            on_tool_call=lambda name, args: observed.append((name, args)),
            stream=False,
        )

        answer = session.run_turn("找一下课件")

        self.assertEqual(answer, "课件已找到")
        self.assertEqual(observed, [("list_files", {"pattern": "*.pptx"})])
        tool_messages = [m for m in session.messages if m.get("role") == "tool"]
        self.assertEqual(len(tool_messages), 1)
        self.assertIn("Week 13-15.pptx", tool_messages[0]["content"])

    def test_unknown_tool_returns_error_to_model_instead_of_crashing(self):
        client = FakeClient(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [tool_call("not_a_tool", {})],
                },
                {"role": "assistant", "content": "好的"},
            ]
        )
        session = AgentSession(client, AgentToolbox(COURSE_ROOT, project_root=ROOT), stream=False)

        session.run_turn("试试未知工具")

        tool_messages = [m for m in session.messages if m.get("role") == "tool"]
        self.assertIn("Unknown tool", tool_messages[0]["content"])

    def test_old_tool_output_is_compacted_when_context_grows(self):
        with tempfile.TemporaryDirectory() as tmp:
            big_file = Path(tmp) / "big.txt"
            big_file.write_text("x" * 5000, encoding="utf-8")
            toolbox = AgentToolbox(Path(tmp), project_root=Path(tmp))
            client = FakeClient(
                [
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [tool_call("read_file", {"path": "big.txt"})],
                    },
                    {"role": "assistant", "content": "读完了"},
                ]
            )
            session = AgentSession(client, toolbox, max_context_chars=1000, stream=False)

            session.run_turn("读取大文件")

            tool_messages = [m for m in session.messages if m.get("role") == "tool"]
            self.assertEqual(tool_messages[0]["content"], COMPACTION_NOTE)

    def test_clear_resets_history_to_system_prompt(self):
        client = FakeClient([{"role": "assistant", "content": "回答"}])
        session = AgentSession(client, AgentToolbox(COURSE_ROOT, project_root=ROOT), stream=False)
        session.run_turn("问题")

        session.clear()

        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.messages[0]["role"], "system")

    def test_streaming_path_emits_text_chunks(self):
        client = FakeClient([{"role": "assistant", "content": "流式回答"}])
        chunks = []
        session = AgentSession(
            client,
            AgentToolbox(COURSE_ROOT, project_root=ROOT),
            on_text=chunks.append,
            stream=True,
        )

        answer = session.run_turn("问题")

        self.assertEqual(answer, "流式回答")
        self.assertEqual(chunks, ["流式回答"])


if __name__ == "__main__":
    unittest.main()
