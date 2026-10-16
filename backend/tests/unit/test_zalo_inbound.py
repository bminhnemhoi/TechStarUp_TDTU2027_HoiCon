"""Phân tích cập nhật Zalo đến: chỉ lấy phần cần dùng, phân loại văn bản NGAY ở webhook để job không mang chữ thô."""

import json
from pathlib import Path
from typing import Any

import pytest

from hoicon.channels.inbound import classify, parse_update

FIXTURES = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "fixtures" / "zalo_update.v1.valid.json"


def fixture(name: str) -> dict[str, Any]:
    update = next(u for u in json.loads(FIXTURES.read_text(encoding="utf-8")) if u["_name"] == name)
    return {k: v for k, v in update.items() if k != "_name"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/start 482913", ("start", "482913")),
        ("  /start    482913  ", ("start", "482913")),
        ("/start@hoicon_dev_bot 482913", ("start", "482913")),
        ("/START 482913", ("start", "482913")),
        ("/start", ("start_no_code", None)),
        ("/start 12345", ("start_no_code", None)),
        ("/start 1234567", ("start_no_code", None)),
        ("/start abcdef", ("start_no_code", None)),
        ("/start 482913 thêm", ("start_no_code", None)),
        ("1", ("choice", "1")),
        (" 2 ", ("choice", "2")),
        ("3\n", ("choice", "3")),
        ("4", ("login", None)),
        (" 4\n", ("login", None)),
        ("web", ("login", None)),
        ("WEB", ("login", None)),
        ("Đăng nhập", ("login", None)),
        ("đăng   nhập", ("login", None)),
        ("dang nhap", ("login", None)),
        ("ĐĂNG NHẬP", ("login", None)),
        ("đăng nhập web", ("other", None)),  # chỉ nhận đúng lệnh, không đoán ý
        ("4 5", ("other", None)),
        ("44", ("other", None)),
        ("٤", ("other", None)),  # chữ số Ả Rập-Ấn Độ không được coi là 4
        ("webinar", ("other", None)),
        ("5", ("other", None)),
        ("1 2", ("other", None)),
        ("١", ("other", None)),  # chữ số Ả Rập-Ấn Độ không được coi là 1
        ("Cho con xem chi tiết với", ("other", None)),
        ("", ("other", None)),
    ],
)
def test_classify(text: str, expected: tuple[str, str | None]) -> None:
    assert classify(text) == expected


def test_parse_text_update_extracts_only_what_is_needed() -> None:
    parsed = parse_update(fixture("text_reply_1"))
    assert parsed is not None
    assert (parsed.message_id, parsed.user_id, parsed.chat_id, parsed.text) == (
        "fixture-msg-0001",
        "fixture-user-0001",
        "fixture-chat-0001",
        "1",
    )
    assert not hasattr(parsed, "display_name")  # tên thật không đi tiếp


def test_parse_ignores_what_it_cannot_use() -> None:
    assert parse_update(fixture("unsupported_event_without_message")) is None  # sự kiện không phải tin chữ
    group = fixture("text_reply_1")
    group["result"]["message"]["chat"]["chat_type"] = "GROUP"
    assert parse_update(group) is None  # nhóm (Beta) không hỗ trợ
    bot = fixture("text_reply_1")
    bot["result"]["message"]["from"]["is_bot"] = True
    assert parse_update(bot) is None  # tin do bot gửi (tránh vòng lặp)
    no_id = fixture("text_reply_1")
    del no_id["result"]["message"]["message_id"]
    assert parse_update(no_id) is None  # không chống trùng được ⇒ không xử lý


@pytest.mark.parametrize(
    "body",
    [None, [], "x", 5, {}, {"ok": True}, {"ok": True, "result": []}, {"ok": True, "result": {"event_name": 5}}],
)
def test_parse_never_raises_on_garbage(body: Any) -> None:
    assert parse_update(body) is None


def test_parse_rejects_oversized_or_non_string_fields() -> None:
    update = fixture("text_reply_1")
    update["result"]["message"]["message_id"] = "x" * 101
    assert parse_update(update) is None  # khóa job chỉ có 200 ký tự
    update = fixture("text_reply_1")
    update["result"]["message"]["from"]["id"] = 12345
    assert parse_update(update) is None
