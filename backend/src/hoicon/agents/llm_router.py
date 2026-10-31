"""Cổng duy nhất tới LLM (CLAUDE.md luật 5, AGENTS.md `llm_router`).

Mỗi lời gọi: che PII (`mask_text`) → nội dung do kẻ gian/người dùng cung cấp bọc `<untrusted>` trong lượt user
(không bao giờ vào system prompt) → trần thời gian 4 s, không thử lại → output có cấu trúc (Pydantic) → tính chi phí
→ mọi lỗi, quá hạn, từ chối, hết ngân sách đều rơi về `fallback` soạn sẵn. Node ghi kết quả vào `agent_steps`.

Chỉ có hồ sơ `fast` ở spike P1-S4; `strong`/`judge` thêm khi có node cần (P2-11, P2-15).
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import anthropic
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.config import Settings, get_settings
from hoicon.db.models import AgentStep
from hoicon.domain.pii import mask_text

logger = logging.getLogger(__name__)

TIMEOUT_S = 4.0
BUDGET_READ_TIMEOUT_S = 1.0  # quá hạn ⇒ `budget_unknown` (rơi về mẫu), không chờ DB nghẽn
VN = ZoneInfo("Asia/Ho_Chi_Minh")  # "ngày" của trần chi tiêu theo giờ người dùng và đội
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass(frozen=True)
class ModelSpec:
    """Giá USD / 1 triệu token (bảng giá Anthropic, tra 14/10/2026) + tham số riêng từng dòng model."""

    input_per_mtok: Decimal
    output_per_mtok: Decimal
    params: dict[str, Any] = field(default_factory=dict)


MODELS: dict[str, ModelSpec] = {
    # Haiku 4.5: không có `effort`, không bật thinking ⇒ trả lời ngay.
    "claude-haiku-4-5": ModelSpec(Decimal("1.00"), Decimal("5.00")),
    # Haiku 5.5: thinking bật mặc định, effort mặc định medium ⇒ tắt thinking + effort low cho bước phân loại nhanh.
    # Giá áp dụng cho prompt ≤ 100K token (prompt của HỏiCon < 2K).
    "claude-haiku-5-5": ModelSpec(
        Decimal("0.10"),
        Decimal("0.50"),
        {"thinking": {"type": "disabled"}, "output_config": {"effort": "low"}},
    ),
}


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    text: str


def _defang(text: str) -> str:
    """Không cho dữ liệu đóng/mở thẻ (`</untrusted><context>…`) để giả làm chỉ dẫn."""
    return text.replace("<", "‹").replace(">", "›")


def load_prompt(name: str) -> Prompt:
    """`prompts/<name>.md` có front-matter `version:`; đổi prompt ⇒ tăng version + chạy `run-eval smoke`."""
    raw = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    _, header, body = raw.split("---", 2)
    meta = dict(line.split(":", 1) for line in header.strip().splitlines())
    return Prompt(name, meta["version"].strip(), body.strip())


@dataclass
class LlmResult[T: BaseModel]:
    output: T
    model: str | None
    prompt_version: str
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal(0)
    fallback_used: bool = False
    error: str | None = None
    input_redacted: dict[str, Any] = field(default_factory=dict)


class MessagesClient(Protocol):
    """Phần của `anthropic.AsyncAnthropic` mà router dùng (test thay bằng client giả)."""

    def with_options(self, **kwargs: Any) -> Any: ...


class LlmRouter:
    def __init__(
        self,
        client: MessagesClient | None,
        fast_model: str,
        daily_budget_usd: Decimal,
        sessions: async_sessionmaker | None = None,
    ) -> None:
        if fast_model not in MODELS:
            raise ValueError(f"model chưa có trong bảng giá: {fast_model}")
        self._client = client
        self.fast_model = fast_model
        self._budget = daily_budget_usd
        self._sessions = sessions
        # Không `sessions` (test đơn vị): đếm chi tiêu trong bộ nhớ tiến trình, reset theo ngày.
        self._spent: dict[date, Decimal] = {}
        # Có `sessions` (spec 003, FR-011): chi tiêu đã ghi = SUM(agent_steps.cost_usd) của ngày giờ Việt Nam (bền qua
        # khởi động lại) + phần đang giữ chỗ cho các lời gọi còn bay trong tiến trình này.
        self._in_flight = Decimal(0)

    @classmethod
    def from_settings(cls, settings: Settings | None = None, sessions: async_sessionmaker | None = None) -> "LlmRouter":
        settings = settings or get_settings()
        key = settings.anthropic_api_key
        client = anthropic.AsyncAnthropic(api_key=key.get_secret_value()) if key else None
        return cls(client, settings.llm_fast_model, Decimal(str(settings.llm_daily_budget_usd)), sessions)

    async def _recorded_spend(self) -> Decimal:
        """Chi tiêu đã ghi trong `agent_steps` từ 00:00 hôm nay giờ Việt Nam (chi phí vào bảng khi node ghi bước)."""
        start = datetime.now(VN).replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.coalesce(func.sum(AgentStep.cost_usd), 0)).where(AgentStep.at >= start)
        async with self._sessions() as session:
            return Decimal(await session.scalar(query))

    async def structured[T: BaseModel](
        self,
        *,
        prompt: Prompt,
        context: dict[str, Any],
        output: type[T],
        fallback: T,
        consented: bool,
        untrusted: str | None = None,
        max_tokens: int = 512,
    ) -> LlmResult[T]:
        """Gọi hồ sơ `fast`; không bao giờ ném lỗi — thất bại nào cũng trả `fallback` với `fallback_used=True`.

        `consented` (spec 011 FR-006, D8): người cao tuổi còn đồng ý `llm_processing`. Bắt buộc, không có mặc định: lời
        gọi quên truyền sẽ không chạy. False ⇒ không gọi nhà cung cấp (kể cả khi có khóa), rơi về `fallback`, lý do
        `consent`. Lượt không có người thật (eval, demo, mô phỏng) truyền True vì chỉ có dữ liệu hư cấu."""
        context_text = _defang(mask_text(json.dumps(context, ensure_ascii=False, sort_keys=True)))
        content = f"<context>\n{context_text}\n</context>"
        if untrusted:
            # Văn bản từ bên ngoài: dữ liệu để đánh giá, KHÔNG phải chỉ dẫn (system prompt nói rõ điều này).
            content += f"\n<untrusted>\n{_defang(mask_text(untrusted))}\n</untrusted>"
        result: LlmResult[T] = LlmResult(
            output=fallback,
            model=self.fast_model,
            prompt_version=f"{prompt.name}@{prompt.version}",
            input_redacted={"context": context_text, "untrusted": bool(untrusted)},
        )

        if not consented:
            return self._fallback(result, "consent")
        today = date.today()
        if self._client is None:
            return self._fallback(result, "no_api_key")
        spec = MODELS[self.fast_model]
        # Giữ chỗ ngân sách TRƯỚC khi gọi (lời gọi song song không cùng lọt; quá hạn vẫn có thể bị tính tiền).
        reserved = (len(prompt.text) + len(content)) // 3 * spec.input_per_mtok / 10**6
        reserved += max_tokens * spec.output_per_mtok / 10**6
        if self._sessions is None:
            spent = self._spent.get(today, Decimal(0))
        else:
            try:
                async with asyncio.timeout(
                    BUDGET_READ_TIMEOUT_S
                ):  # đọc chi tiêu không được làm đường LLM vượt luật 5 (≤ 4 s)
                    spent = await self._recorded_spend() + self._in_flight
            except Exception as exc:  # đóng mặc định về chi phí: không đọc được chi tiêu ⇒ không gọi LLM
                logger.warning("llm budget unreadable: %s", type(exc).__name__)  # không ghi thông điệp (chuỗi kết nối)
                return self._fallback(result, "budget_unknown")
        # Từ đây tới lúc giữ chỗ không có `await` ⇒ hai lời gọi song song không cùng lọt qua một khoảng trần.
        if spent + reserved > self._budget:
            return self._fallback(result, "budget_exhausted")
        if self._sessions is None:
            self._spent[today] = spent + reserved
        else:
            self._in_flight += reserved
        try:
            return await self._call(prompt, content, output, max_tokens, spec, reserved, today, result)
        finally:
            if self._sessions is not None:
                # Chi phí thật vào `agent_steps` khi node ghi bước. Trần là ngân sách MỀM: các lời gọi vừa xong nhưng
                # chưa được ghi (và tiến trình khác) không được tính ⇒ sai số tối đa bằng số lời gọi đồng thời.
                self._in_flight -= reserved

    async def _call[T: BaseModel](
        self,
        prompt: Prompt,
        content: str,
        output: type[T],
        max_tokens: int,
        spec: ModelSpec,
        reserved: Decimal,
        today: date,
        result: LlmResult[T],
    ) -> LlmResult[T]:
        started = time.monotonic()
        try:
            async with asyncio.timeout(TIMEOUT_S):  # trần cứng, kể cả khi socket trả từng byte một
                response = await self._client.with_options(timeout=TIMEOUT_S, max_retries=0).messages.parse(
                    model=self.fast_model,
                    max_tokens=max_tokens,
                    system=prompt.text,
                    messages=[{"role": "user", "content": content}],
                    output_format=output,
                    **spec.params,
                )
        except Exception as exc:  # hứa "không bao giờ ném lỗi" (CancelledError là BaseException, vẫn lan ra)
            # Chỉ ghi tên lớp lỗi: thông điệp lỗi có thể lặp lại nội dung đã gửi.
            result.latency_ms = int((time.monotonic() - started) * 1000)
            if self._sessions is not None and isinstance(exc, TimeoutError | anthropic.APITimeoutError):
                # Quá hạn: nhà cung cấp vẫn có thể đã xử lý và tính tiền ⇒ ghi phần giữ chỗ để `agent_steps` (nguồn của
                # trần) có nó. Lỗi chắc chắn không bị tính (hết kết nối, khóa sai) thì không ghi, kẻo tắt LLM cả ngày.
                result.cost_usd = reserved
            return self._fallback(result, type(exc).__name__)
        result.latency_ms = int((time.monotonic() - started) * 1000)

        usage = response.usage
        result.tokens_in, result.tokens_out = usage.input_tokens, usage.output_tokens
        result.cost_usd = (
            usage.input_tokens * spec.input_per_mtok + usage.output_tokens * spec.output_per_mtok
        ) / 10**6
        if self._sessions is None:
            self._spent[today] += result.cost_usd - reserved  # quyết toán theo usage thật
        if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
            return self._fallback(result, f"stop_{response.stop_reason}")
        result.output = response.parsed_output
        return result

    @staticmethod
    def _fallback[T: BaseModel](result: LlmResult[T], reason: str) -> LlmResult[T]:
        result.fallback_used, result.error = True, reason
        logger.info("llm fallback: %s (%s)", reason, result.prompt_version)
        return result
