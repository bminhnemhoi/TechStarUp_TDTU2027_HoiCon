"""`ReplayClient`: phản hồi LLM ghi sẵn (cassette) thay cho Anthropic trong eval (spec 030, FR-004).

Cắm vào `LlmRouter` hiện có (không có đường vòng quanh router): router vẫn che PII, đo giờ, tính chi phí, rơi về mẫu.
Client chỉ giả hình dạng `messages.parse` mà router gọi; KHÔNG bao giờ tạo `anthropic.AsyncAnthropic`, không có mạng.
Mỗi phần tử của cassette là output có cấu trúc hoặc `{"error": ...}`:
- `refusal`  ⇒ trả `stop_reason="refusal"` (router rơi về mẫu)
- `timeout`  ⇒ ném `TimeoutError`; `missing` hoặc hết danh sách ⇒ ném `LookupError`
- `malformed` ⇒ trả `parsed_output=None` (output sai cấu trúc)
"""

import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from hoicon.agents.incident_graph import GuardianBrief, RiskAssessment

NODE_BY_OUTPUT: dict[type, str] = {RiskAssessment: "risk_scorer", GuardianBrief: "intervention"}
# Usage cố định: router tính chi phí được (đường ngân sách chạy thật) nhưng báo cáo ghi chi phí thật = 0 (phát lại).
USAGE = SimpleNamespace(input_tokens=800, output_tokens=100)


@dataclass(frozen=True)
class RecordedCall:
    node: str
    system: str
    messages: list[dict[str, Any]]


class ReplayClient:
    def __init__(self, cassette: dict[str, Any] | None = None) -> None:
        self.calls: list[RecordedCall] = []
        self._responses: dict[str, list[dict[str, Any]]] = {}
        self._cursor: dict[str, int] = {}
        self.load(cassette or {"responses": {}})

    @classmethod
    def from_path(cls, path: Path) -> "ReplayClient":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def load(self, cassette: dict[str, Any]) -> None:
        """Nạp cassette của ca kế tiếp: đặt lại con trỏ và danh sách lời gọi đã ghi."""
        responses = cassette.get("responses", {})
        self._responses = {node: list(responses.get(node, [])) for node in NODE_BY_OUTPUT.values()}
        self._cursor = dict.fromkeys(self._responses, 0)
        self.calls = []

    # --- Hình dạng AsyncAnthropic mà LlmRouter dùng: client.with_options(...).messages.parse(...) ---------------

    def with_options(self, **_: Any) -> "ReplayClient":
        return self

    @property
    def messages(self) -> "ReplayClient":
        return self

    async def parse(
        self, *, output_format: type, system: str = "", messages: list[dict[str, Any]] | None = None, **_: Any
    ) -> Any:
        node = NODE_BY_OUTPUT.get(output_format)
        if node is None:
            raise ValueError(f"không có cassette cho output {output_format!r}")
        self.calls.append(RecordedCall(node, system, list(messages or [])))
        index = self._cursor[node]
        self._cursor[node] = index + 1
        if index >= len(self._responses[node]):
            raise LookupError(f"cassette hết phản hồi cho node {node} (lần gọi thứ {index + 1})")
        item = self._responses[node][index]
        error = item.get("error")
        if error == "timeout":
            raise TimeoutError(node)
        if error == "missing":
            raise LookupError(f"cassette đánh dấu thiếu phản hồi cho node {node}")
        if error == "refusal":
            return SimpleNamespace(parsed_output=None, stop_reason="refusal", usage=USAGE)
        if error == "malformed":
            return SimpleNamespace(parsed_output=None, stop_reason="end_turn", usage=USAGE)
        return SimpleNamespace(parsed_output=output_format.model_validate(item), stop_reason="end_turn", usage=USAGE)

    def sent_text(self) -> str:
        """Nội dung ĐỘNG đã gửi cho 'LLM' (messages; system prompt là văn bản tĩnh của repo) — để bộ kiểm PII quét."""
        return "\n".join(m["content"] for c in self.calls for m in c.messages)
