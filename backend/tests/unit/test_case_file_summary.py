"""Spec 031 FR-005: đoạn tóm tắt do LLM chỉ được dùng khi sạch; mọi trường hợp khác rơi về câu mẫu (SC-006)."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from hoicon.agents import texts
from hoicon.agents.llm_router import LlmRouter
from hoicon.services.case_file_service import CaseSummary, llm_summary, safe_summary

ALIAS = "Mẹ"
FACTS = {"level": "critical", "app_category": "bank", "authority": True, "transfer": True, "decision": "scam"}
USAGE = SimpleNamespace(input_tokens=500, output_tokens=80)


class FakeClient:
    """Giả `AsyncAnthropic`: trả đúng một đầu ra, hoặc ném lỗi/quá hạn."""

    def __init__(self, reply: str | Exception | None) -> None:
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def with_options(self, **_: Any) -> "FakeClient":
        return self

    @property
    def messages(self) -> "FakeClient":
        return self

    async def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        if self.reply is None:
            await asyncio.sleep(10)  # quá hạn: router cắt ở 4 s
        return SimpleNamespace(parsed_output=CaseSummary(summary=self.reply), stop_reason="end_turn", usage=USAGE)


def router(client: FakeClient | None) -> LlmRouter:
    return LlmRouter(client, "claude-haiku-5-5", Decimal(10))


async def test_a_clean_sentence_is_used_and_the_alias_is_filled() -> None:
    client = FakeClient("{alias} nghe một cuộc gọi lạ rồi mở ứng dụng ngân hàng. HỏiCon đã nhắc {alias} dừng lại.")
    out = await llm_summary(router(client), FACTS, ALIAS)
    assert out == "Mẹ nghe một cuộc gọi lạ rồi mở ứng dụng ngân hàng. HỏiCon đã nhắc Mẹ dừng lại."


async def test_the_model_only_sees_facts_and_a_placeholder_alias() -> None:
    client = FakeClient("{alias} nghe một cuộc gọi lạ.")
    await llm_summary(router(client), FACTS, ALIAS)
    sent = client.calls[0]["messages"][0]["content"]
    assert "{alias}" in sent and "Mẹ" not in sent and "critical" in sent
    assert "<untrusted>" not in sent  # không có văn bản của kẻ gian trong hồ sơ


@pytest.mark.parametrize(
    "bad",
    [
        "Mẹ nhận cuộc gọi từ số 0900000123.",
        "Mẹ được bảo vào https://vi-du.example để nộp tiền.",
        "Mẹ được hướng dẫn nhắn qua zalo nhóm.",
        "Anh/chị đừng báo ai, cứ chuyển tiền cho yên.",
        "Mọi việc an toàn rồi, Mẹ không sao đâu.",
        "HỏiCon sẽ giúp lấy lại được tiền cho Mẹ.",
        "HỏiCon đã báo công an giúp Mẹ.",
        "x" * 601,
        "Mẹ đã mất 50 triệu.",
        "Mẹ đã chuyển ba trăm triệu cho người lạ.",
        "Công an đã tiếp nhận vụ việc của Mẹ.",
        "Mẹ đã trình báo.",
        "Mẹ đã gọi 2 lần.",
        "   ",
    ],
)
async def test_unsafe_or_empty_text_is_replaced_by_the_template(bad: str) -> None:
    assert safe_summary(bad, ALIAS) is None


async def test_no_key_means_no_call_and_a_template() -> None:
    assert await llm_summary(router(None), FACTS, ALIAS) is None


async def test_an_error_from_the_provider_means_a_template() -> None:
    assert await llm_summary(router(FakeClient(RuntimeError("boom"))), FACTS, ALIAS) is None


async def test_a_timeout_means_a_template() -> None:
    assert await llm_summary(router(FakeClient(None)), FACTS, ALIAS) is None


def test_the_template_summary_is_clean_and_names_no_one() -> None:
    text = texts.case_file_summary(ALIAS, "bank", "critical", True, True)
    assert safe_summary(text, ALIAS) == text
    assert "ngân hàng" in text and "công an" in text


def test_normalization_catches_decomposed_text() -> None:
    import unicodedata

    assert safe_summary(unicodedata.normalize("NFD", "Đừng báo ai nhé."), ALIAS) is None


@pytest.mark.parametrize("alias", ["Mẹ", "Ba", "Bà ngoại"])
@pytest.mark.parametrize("app", ["bank", "wallet", "securities", "sideloaded", "none"])
@pytest.mark.parametrize("level", ["low", "medium", "high", "critical"])
@pytest.mark.parametrize(("authority", "transfer"), [(False, False), (True, False), (False, True), (True, True)])
def test_template_reads_well_for_every_combination(
    alias: str, app: str, level: str, authority: bool, transfer: bool
) -> None:
    text = texts.case_file_summary(alias, app, level, authority, transfer)
    assert safe_summary(text, alias) == text
    assert text.startswith(f"{alias} nghe một cuộc gọi lạ") and "mức rủi ro: " in text
    assert "Chưa thấy nguy cơ" not in text and text.count("Người gọi") <= 1 + (authority and transfer)
