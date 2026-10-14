"""Một cửa kiểm/giảm dữ liệu trước khi giá trị resume vào bảng checkpoint của LangGraph (review bảo mật P1-S4, H1)."""

from hoicon.agents.runtime import clean_resume


def test_free_text_note_becomes_flags_only() -> None:
    clean = clean_resume({"answer": "yes", "note": "Họ bảo đọc mã OTP 123456, gọi 0900000001", "extra": "x" * 10_000})
    assert clean == {
        "answer": "yes",
        "note_flags": {
            "mentions_authority": False,
            "mentions_transfer": False,
            "mentions_code": True,
            "mentions_secrecy": False,
            "mentions_app_or_link": False,
        },
    }


def test_only_known_values_survive() -> None:
    assert clean_resume({"decision": "scam", "timer": "t9", "answer": "maybe"}) == {"decision": "scam"}
    assert clean_resume({"timeout": True}) == {"timeout": True}
    assert clean_resume({"timeout": "yes"}) == {"invalid": True}
    assert clean_resume("drop table") == {"invalid": True}
