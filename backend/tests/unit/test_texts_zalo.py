"""Mẫu tin Zalo cho người giám hộ (spec 002): công khai AI (luật 6), nhãn diễn tập (luật 8), hướng dẫn trả lời 1/2/3."""

import pytest

from hoicon.agents import texts
from hoicon.domain.pii import mask_text
from hoicon.domain.risk import RiskLevel


def all_messages(is_drill: bool) -> dict[str, str]:
    return {
        "fast_alert": texts.guardian_fast_alert("Mẹ", "002", "bank", is_drill),
        "detail": texts.guardian_detail("Mẹ", RiskLevel.HIGH, "Tóm tắt.", "call_now", is_drill),
        "reminder": texts.guardian_reminder("Mẹ", is_drill),
        "escalation": texts.guardian_escalation("Mẹ", is_drill),
        "ack_safe": texts.guardian_ack("safe", is_drill),
        "ack_scam": texts.guardian_ack("scam", is_drill),
        "detail_pending": texts.detail_pending(is_drill),
        "incident_closed": texts.reply_incident_closed(is_drill),
    }


def general_messages() -> dict[str, str]:
    return {
        "pairing_confirmed": texts.pairing_confirmed(),
        "pairing_help": texts.pairing_help(),
        "pairing_already": texts.pairing_already(),
        "reply_help": texts.reply_help(),
        "reply_no_incident": texts.reply_no_incident(),
    }


@pytest.mark.parametrize("is_drill", [False, True])
def test_every_zalo_message_opens_with_ai_disclosure_and_drill_label(is_drill: bool) -> None:
    for name, message in all_messages(is_drill).items():
        assert message.startswith("Đây là trợ lý AI HỏiCon."), name
        assert ("[DIỄN TẬP]" in message) is is_drill, name  # luật 8
    for name, message in general_messages().items():
        assert message.startswith("Đây là trợ lý AI HỏiCon."), name
        assert "[DIỄN TẬP]" not in message, name


def test_incident_messages_tell_the_guardian_how_to_reply_and_never_mention_buttons() -> None:
    """Zalo không có nút bấm (docs/spikes/P1-S3-zalo.md §1) ⇒ tin cần hành động phải ghi rõ cách trả lời bằng chữ."""
    messages = all_messages(False)
    for name in ("fast_alert", "reminder", "escalation"):
        assert texts.REPLY_GUIDE in messages[name], name
    assert texts.REPLY_GUIDE_NO_DETAIL in messages["detail"]  # đã là chi tiết: không mời "xem chi tiết" lần nữa
    assert "3 - Xem chi tiết" not in messages["detail"]
    for name, message in {**messages, **general_messages()}.items():
        assert "nút" not in message.lower(), name


def test_reply_guide_names_all_choices_and_never_closes_an_alert_by_default() -> None:
    guide = texts.REPLY_GUIDE
    for choice in ("1 - ", "2 - ", "3 - "):
        assert choice in guide
    assert "an toàn" in guide and "lừa đảo" in guide and "chi tiết" in guide
    assert "Chưa gọi được" in guide  # người chưa gọi được Mẹ không bị ép chọn "an toàn"
    assert "1 - Đã gọi được" in guide  # lựa chọn "an toàn" chỉ dành cho người ĐÃ gọi được


def test_first_alert_leads_with_the_action_so_a_notification_preview_shows_it() -> None:
    message = texts.guardian_fast_alert("Mẹ", "002", "bank", False)
    assert "gọi hỏi Mẹ ngay" in message[:140]


def test_drill_messages_say_it_is_only_practice() -> None:
    for name, message in all_messages(True).items():
        assert texts.DRILL_NOTE in message, name
    assert texts.DRILL_NOTE not in texts.guardian_fast_alert("Mẹ", "002", "bank", False)


def test_detail_summary_without_final_punctuation_is_terminated() -> None:
    message = texts.guardian_detail("Mẹ", RiskLevel.HIGH, "Có dấu hiệu giả danh công an", "call_now", False)
    assert "giả danh công an. Anh/chị gọi ngay" in message


def test_messages_contain_no_digit_sequences_that_could_be_numbers() -> None:
    """Mẫu tin không được chứa chuỗi ≥ 4 chữ số (số điện thoại/mã): `mask_text` không đổi gì."""
    for message in [*all_messages(False).values(), *general_messages().values()]:
        assert mask_text(message) == message


def test_pairing_help_does_not_reveal_whether_a_code_exists() -> None:
    help_text = texts.pairing_help()
    for leak in ("đã dùng", "không tồn tại", "sai mã"):
        assert leak not in help_text
    assert "15 phút" in help_text and "/start" in help_text


def test_acks_do_not_promise_more_than_the_system_does() -> None:
    assert "an toàn" in texts.guardian_ack("safe", False)
    assert "lừa đảo" in texts.guardian_ack("scam", False)
    with pytest.raises(KeyError):
        texts.guardian_ack("maybe", False)
