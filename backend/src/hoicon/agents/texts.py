"""Câu chữ đã duyệt của đồ thị sự cố (LLM chỉ chọn mã câu hỏi và viết phần tóm tắt nằm giữa mẫu).

Luật 6 (công khai AI): mọi tin tới người giám hộ và lời hỏi người cao tuổi mở đầu bằng `AI_DISCLOSURE` (có test).
Bản nháp — `ux-elder-reviewer` duyệt câu chữ cuối ở P2-07/P2-08. Diễn tập: nhãn `DRILL_LABEL` ngay SAU câu công khai
(luật 8) để tin vẫn mở đầu bằng câu công khai.
"""

from hoicon.domain.risk import RiskLevel

AI_DISCLOSURE = "Đây là trợ lý AI HỏiCon."
DRILL_LABEL = "[DIỄN TẬP]"

# E8: câu hỏi người cao tuổi trả lời bằng 3 nút "Có" / "Không" / "Không rõ" (giọng nói là tùy chọn, P1-S5).
QUESTIONS: dict[str, str] = {
    "q_caller_authority": "Người vừa gọi có xưng là công an, ngân hàng, thuế hay cơ quan nhà nước không ạ?",
    "q_asked_transfer": "Người gọi có bảo bác chuyển tiền, hoặc đọc mã số gửi về điện thoại không ạ?",
    "q_know_caller": "Bác có biết rõ người vừa gọi là ai không ạ?",
}
ANSWERS = ("yes", "no", "unsure")

LEVEL_VI = {
    RiskLevel.NONE: "chưa thấy nguy cơ",
    RiskLevel.LOW: "thấp",
    RiskLevel.MEDIUM: "trung bình",
    RiskLevel.HIGH: "cao",
    RiskLevel.CRITICAL: "rất cao",
}
APP_KIND_VI = {"bank": "ngân hàng", "wallet": "ví điện tử", "securities": "chứng khoán"}
ACTION_VI = {
    "call_now": "Anh/chị gọi ngay cho {alias} và nhắc {alias} chưa chuyển tiền.",
    "call_and_stay_on_line": "Anh/chị gọi ngay cho {alias} và giữ máy tới khi {alias} thoát ứng dụng ngân hàng.",
    "visit_or_call_relative": "Nếu {alias} không nghe máy, nhờ người ở gần qua xem giúp.",
}


def _message(text: str, is_drill: bool) -> str:
    return f"{AI_DISCLOSURE} {DRILL_LABEL} {text}" if is_drill else f"{AI_DISCLOSURE} {text}"


def question_for_elder(question_id: str, is_drill: bool) -> str:
    return _message(QUESTIONS[question_id], is_drill)


def guardian_fast_alert(alias: str, last3: str | None, app_category: str, is_drill: bool) -> str:
    caller = f"số lạ đuôi {last3}" if last3 else "một số lạ"
    app = APP_KIND_VI.get(app_category, "tài chính")
    return _message(
        f"{alias} vừa nghe cuộc gọi từ {caller} rồi mở ứng dụng {app}. HỏiCon đã nhắc {alias} tạm dừng. "
        f"Anh/chị gọi ngay cho {alias} để hỏi thăm nhé.",
        is_drill,
    )


def guardian_detail(alias: str, level: RiskLevel, summary: str, action: str, is_drill: bool) -> str:
    return _message(
        f"Mức nguy cơ: {LEVEL_VI[level]}. {summary} {ACTION_VI[action].format(alias=alias)}",
        is_drill,
    )


def guardian_reminder(alias: str, is_drill: bool) -> str:
    return _message(
        f"Nhắc lại: {alias} có thể đang bị dụ chuyển tiền. Anh/chị đã liên lạc được với {alias} chưa? "
        "Bấm nút bên dưới để báo cho HỏiCon.",
        is_drill,
    )


def guardian_escalation(alias: str, is_drill: bool) -> str:
    return _message(
        f"Người thân thứ nhất chưa phản hồi. {alias} có thể đang bị dụ chuyển tiền — "
        f"anh/chị gọi ngay cho {alias} giúp.",
        is_drill,
    )
