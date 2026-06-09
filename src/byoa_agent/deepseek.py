from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from typing import Any


Transport = Callable[[str, dict[str, str], dict[str, Any]], dict[str, Any]]
StreamTransport = Callable[[str, dict[str, str], dict[str, Any]], Iterable[str]]


class DeepSeekError(RuntimeError):
    """Raised when DeepSeek returns an unusable response."""


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        transport: Transport | None = None,
        stream_transport: StreamTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport or self._http_transport
        self.stream_transport = stream_transport or self._http_stream_transport

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        body = self._request_body(messages, tools)
        response = self.transport(f"{self.base_url}/chat/completions", self._headers(), body)
        try:
            return response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekError(f"Malformed DeepSeek response: {response!r}") from exc

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        on_text: Callable[[str], None],
    ) -> dict[str, Any]:
        """Stream one assistant message over SSE, emitting text deltas as they arrive.

        Tool-call argument fragments are reassembled by index, mirroring the
        OpenAI-compatible streaming format DeepSeek uses.
        """
        body = self._request_body(messages, tools)
        body["stream"] = True
        lines = self.stream_transport(f"{self.base_url}/chat/completions", self._headers(), body)
        content_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        for raw_line in lines:
            line = raw_line.strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            if chunk.get("error"):
                raise DeepSeekError(f"DeepSeek stream error: {chunk['error']!r}")
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            text = delta.get("content")
            if text:
                content_parts.append(text)
                on_text(text)
            for fragment in delta.get("tool_calls") or []:
                index = int(fragment.get("index", 0))
                slot = tool_calls.setdefault(
                    index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                )
                if fragment.get("id"):
                    slot["id"] = fragment["id"]
                function = fragment.get("function") or {}
                if function.get("name"):
                    slot["function"]["name"] += function["name"]
                if function.get("arguments"):
                    slot["function"]["arguments"] += function["arguments"]
        message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
        if tool_calls:
            message["tool_calls"] = [tool_calls[index] for index in sorted(tool_calls)]
        return message

    def _request_body(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return body

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _http_transport(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DeepSeekError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DeepSeekError(f"Could not reach DeepSeek API: {exc.reason}") from exc
        return json.loads(payload)

    @staticmethod
    def _http_stream_transport(
        url: str, headers: dict[str, str], body: dict[str, Any]
    ) -> Iterator[str]:
        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                for raw in response:
                    yield raw.decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DeepSeekError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DeepSeekError(f"Could not reach DeepSeek API: {exc.reason}") from exc
