"""Câu chữ đã duyệt của đồ thị sự cố (LLM chỉ chọn mã câu hỏi và viết phần tóm tắt nằm giữa mẫu).

Luật 6 (công khai AI): mọi tin tới người giám hộ và lời hỏi người cao tuổi mở đầu bằng `AI_DISCLOSURE` (có test).
Bản nháp — `ux-elder-reviewer` duyệt câu chữ cuối ở P2-07/P2-08. Diễn tập: nhãn `DRILL_LABEL` ngay SAU câu công khai
(luật 8) để tin vẫn mở đầu bằng câu công khai, kèm một câu nói rõ đây chỉ là bài tập.
Mẫu Zalo (spec 002) đã qua `ux-elder-reviewer` ngày 15/10/2026 (xem specs/002-zalo-guardian-channel/evidence.md).
"""

from hoicon.domain.risk import RiskLevel

AI_DISCLOSURE = "Đây là trợ lý AI HỏiCon."
DRILL_LABEL = "[DIỄN TẬP]"
DRILL_NOTE = "Đây chỉ là bài tập, không có nguy hiểm thật."

# E8: câu hỏi người cao tuổi trả lời bằng 3 nút "Có" / "Không" / "Không rõ" (giọng nói là tùy chọn, P1-S5).
QUESTIONS: dict[str, str] = {
    "q_caller_authority": "Người vừa gọi có xưng là công an, ngân hàng, thuế hay cơ quan nhà nước không ạ?",
    "q_asked_transfer": "Người gọi có bảo bác chuyển tiền, hoặc đọc mã số gửi về điện thoại không ạ?",
    "q_know_caller": "Bác có biết rõ người vừa gọi là ai không ạ?",
}
ANSWERS = ("yes", "no", "unsure")

# Zalo Bot không có nút bấm (docs/spikes/P1-S3-zalo.md §1) ⇒ người giám hộ trả lời bằng chữ 1/2/3. Lựa chọn 1 chỉ
# dành cho người ĐÃ gọi được; người chưa gọi được thì gọi lại rồi trả lời sau (không có lựa chọn "chưa" để khỏi
# đóng nhầm cảnh báo).
_REPLY_CHOICES = "Anh/chị trả lời:\n1 - Đã gọi được, mọi thứ an toàn\n2 - Vẫn thấy đáng ngờ (nghi lừa đảo)\n"
_REPLY_LATER = "Chưa gọi được thì anh/chị cứ gọi lại, rồi trả lời sau nhé."
REPLY_GUIDE = f"{_REPLY_CHOICES}3 - Xem chi tiết\n{_REPLY_LATER}"
REPLY_GUIDE_NO_DETAIL = f"{_REPLY_CHOICES}{_REPLY_LATER}"  # tin đã là chi tiết rồi: không mời "xem chi tiết" nữa

LEVEL_VI = {
    RiskLevel.NONE: "chưa thấy nguy cơ",
    RiskLevel.LOW: "thấp",
    RiskLevel.MEDIUM: "trung bình",
    RiskLevel.HIGH: "cao",
    RiskLevel.CRITICAL: "rất cao",
}
APP_KIND_VI = {"bank": "ngân hàng", "wallet": "ví điện tử", "securities": "chứng khoán"}
ACTION_VI = {
    "call_now": "Anh/chị gọi ngay cho {alias} và nhờ {alias} đừng chuyển tiền.",
    "call_and_stay_on_line": "Anh/chị gọi ngay cho {alias} và giữ máy cho đến khi {alias} đóng ứng dụng ngân hàng.",
    "visit_or_call_relative": (
        "Anh/chị gọi {alias} ngay. Nếu {alias} không nghe máy, nhờ người ở gần nhà {alias} qua xem giúp."
    ),
}


def _message(text: str, is_drill: bool) -> str:
    return f"{AI_DISCLOSURE} {DRILL_LABEL} {DRILL_NOTE} {text}" if is_drill else f"{AI_DISCLOSURE} {text}"


def question_for_elder(question_id: str, is_drill: bool) -> str:
    return _message(QUESTIONS[question_id], is_drill)


def guardian_fast_alert(alias: str, last3: str | None, app_category: str, is_drill: bool) -> str:
    """Việc cần làm đứng ngay đầu (phần xem trước thông báo Zalo chỉ hiện vài chục ký tự đầu)."""
    caller = f"số lạ đuôi {last3}" if last3 else "một số lạ"
    app = APP_KIND_VI.get(app_category, "tài chính")
    return _message(
        f"{alias} vừa nghe một cuộc gọi lạ rồi mở ứng dụng {app}. Anh/chị gọi hỏi {alias} ngay nhé.\n\n"
        f"Thêm: cuộc gọi từ {caller}; HỏiCon đang nhắc {alias} tạm dừng.\n\n{REPLY_GUIDE}",
        is_drill,
    )


# Chỗ trống cho liên kết `/a/[token]`: bên gửi (`channels.guardian`) điền token sinh lúc gửi (spec 023).
ACTION_LINK_SLOT = "{action_link}"


def guardian_fast_alert_with_link(
    alias: str, last3: str | None, app_category: str, is_drill: bool, action_url: str
) -> str:
    """Cảnh báo giai đoạn 1 kèm liên kết hành động khẩn cấp (spec 023)."""
    caller = f"số lạ đuôi {last3}" if last3 else "một số lạ"
    app = APP_KIND_VI.get(app_category, "tài chính")
    return _message(
        f"{alias} vừa nghe một cuộc gọi lạ rồi mở ứng dụng {app}. Anh/chị gọi hỏi {alias} ngay nhé.\n\n"
        f"Thêm: cuộc gọi từ {caller}; HỏiCon đang nhắc {alias} tạm dừng.\n\n"
        f"Kiểm tra và xử lý khẩn cấp tại:\n{action_url}\n\n"
        f"{REPLY_GUIDE}",
        is_drill,
    )


def guardian_detail(alias: str, level: RiskLevel, summary: str, action: str, is_drill: bool) -> str:
    summary = summary.strip()
    if summary and summary[-1] not in ".!?":  # tóm tắt do LLM viết có thể thiếu dấu chấm cuối
        summary += "."
    return _message(
        f"Mức nguy cơ: {LEVEL_VI[level]}. {summary} {ACTION_VI[action].format(alias=alias)}\n\n{REPLY_GUIDE_NO_DETAIL}",
        is_drill,
    )


def guardian_reminder(alias: str, is_drill: bool) -> str:
    return _message(
        f"Nhắc lại: anh/chị đã gọi được cho {alias} chưa? "
        f"Lúc nãy {alias} nghe một cuộc gọi lạ rồi mở ứng dụng tài chính.\n\n{REPLY_GUIDE}",
        is_drill,
    )


def guardian_evidence(alias: str, kind: str, last3: str | None, is_drill: bool) -> str:
    """Tin MỘT LẦN khi người cao tuổi tự tra ra số/link nguy hiểm lúc sự cố còn mở (spec 026). Chỉ nêu "số đuôi …" hoặc
    "một đường link": không nêu số đầy đủ, tên miền hay nguồn dữ liệu. Việc cần làm đứng đầu."""
    if kind == "url":
        subject = "một đường link, và HỏiCon thấy đường link này rất đáng ngờ"
    elif last3:
        subject = f"một số điện thoại đuôi {last3}, và HỏiCon thấy số này nằm trong danh sách cảnh báo lừa đảo"
    else:
        subject = "một số điện thoại, và HỏiCon thấy số này nằm trong danh sách cảnh báo lừa đảo"
    return _message(
        f"Anh/chị gọi hỏi {alias} ngay nhé: {alias} vừa tự tra {subject}. "
        f"Nhờ {alias} đừng chuyển tiền, đừng đọc mã OTP cho ai.\n\n{REPLY_GUIDE}",
        is_drill,
    )


def drill_debrief(alias: str, passed: bool | None, red_flags_vi: list[str]) -> str:
    """Tin tổng kết bài luyện tập cho người giám hộ (spec 028 FR-006). LUÔN là diễn tập (`_message(..., True)` ⇒ câu
    công khai AI rồi nhãn [DIỄN TẬP]). `passed`: True = chọn đúng mọi bước, False = còn chỗ phân vân, None = dừng giữa
    chừng. Không điểm số, không so sánh, không lo lắng: việc cần làm (gọi hỏi thăm, cùng ôn) đứng đầu."""
    flags = "\n".join(f"- {flag}" for flag in red_flags_vi)
    if passed is True:
        head = f"{alias} vừa luyện tập nhận biết lừa đảo và chọn đúng ở mọi bước. Anh/chị gọi khen {alias} một câu nhé."
    elif passed is False:
        head = (
            f"{alias} vừa luyện tập nhận biết lừa đảo, còn một vài chỗ chưa chắc tay. "
            f"Anh/chị gọi hỏi thăm {alias} và cùng ôn lại nhé."
        )
    else:
        head = (
            f"{alias} đã dừng buổi luyện tập giữa chừng, không sao cả. "
            f"Khi tiện, anh/chị hỏi thăm {alias} và cùng xem lại nhé."
        )
    return _message(f"{head}\n\nCác dấu hiệu lừa đảo trong bài:\n{flags}", True)


def guardian_escalation(alias: str, is_drill: bool) -> str:
    return _message(
        f"HỏiCon đã nhắn cho một người nhà khác của {alias} nhưng chưa nhận được trả lời. "
        f"{alias} vừa nghe một cuộc gọi lạ rồi mở ứng dụng tài chính. "
        f"Anh/chị gọi hỏi {alias} giúp nhé.\n\n{REPLY_GUIDE}",
        is_drill,
    )


# --- Ghép đôi và phản hồi qua Zalo (spec 002). Giọng ấm, ngắn, kết quả/việc cần làm đứng đầu, không hứa quá khả năng.


def pairing_confirmed() -> str:
    return _message(
        "Đã kết nối xong. Khi HỏiCon thấy người thân của anh/chị có dấu hiệu bị lừa đảo, HỏiCon sẽ nhắn cho anh/chị "
        "tại đây. Mỗi tin cảnh báo sẽ ghi rõ cách trả lời 1, 2 hoặc 3.",
        False,
    )


def pairing_help() -> str:
    """Dùng cho MỌI trường hợp ghép không thành (mã sai, hết hạn, đã dùng, gia đình đủ người, Zalo đã ở gia đình khác):
    cùng một câu để người dò không biết mã có tồn tại hay hợp lệ hay không."""
    return _message(
        "HỏiCon chưa kết nối được Zalo này. Mã kết nối chỉ có hiệu lực 15 phút. Anh/chị nhờ người đã cài HỏiCon "
        "lấy mã mới, rồi nhắn một tin gồm chữ /start, một dấu cách, rồi mã 6 số. Nếu thử lại vẫn chưa được, "
        "anh/chị nhờ người đã cài HỏiCon xem lại phần người nhận cảnh báo giúp nhé.",
        False,
    )


def pairing_already() -> str:
    return _message(
        "Zalo này đã nhận cảnh báo của HỏiCon từ trước, anh/chị không cần nhắn mã nữa. "
        "Khi có cảnh báo, HỏiCon sẽ nhắn tại đây.",
        False,
    )


def reply_help() -> str:
    return _message(
        f"HỏiCon chỉ đọc được số 1, 2 hoặc 3 (hoặc số 4 để lấy liên kết đăng nhập web). "
        f"Nếu cần gấp, anh/chị gọi ngay cho người thân nhé.\n\n{REPLY_GUIDE}",
        False,
    )


def guardian_login_link(url: str) -> str:
    """Liên kết đăng nhập web một lần (spec 027), trả lời lệnh "4"; không gắn sự cố nên không có nhãn diễn tập."""
    return _message(
        "Liên kết đăng nhập web của anh/chị (dùng một lần, hết hạn sau 15 phút):\n"
        f"{url}\n\n"
        "Anh/chị chỉ mở trên máy của mình và đừng chuyển tiếp liên kết này cho ai. "
        "Xin liên kết mới bất cứ lúc nào bằng cách nhắn số 4.",
        False,
    )


def login_rate_limited() -> str:
    return _message(
        "HỏiCon đã gửi anh/chị nhiều liên kết đăng nhập trong một giờ qua. Anh/chị dùng liên kết mới nhất đã nhận, "
        "hoặc chờ một lát rồi nhắn số 4 lại nhé.",
        False,
    )


def reply_no_incident() -> str:
    return _message(
        "Hiện không có cảnh báo nào đang chờ anh/chị trả lời. HỏiCon chỉ nhắn khi phát hiện dấu hiệu đáng ngờ, "
        "anh/chị vẫn nên hỏi thăm người thân thường xuyên nhé.",
        False,
    )


GUARDIAN_ACK = {
    "safe": "HỏiCon đã ghi lại: anh/chị đã gọi được và người thân an toàn. Nếu thấy có gì lạ, anh/chị cứ gọi lại nhé.",
    "scam": (
        "HỏiCon đã ghi lại anh/chị nghi đây là lừa đảo (HỏiCon không tự báo cho cơ quan nào). "
        "Anh/chị gọi người thân và nhờ đừng chuyển tiền nhé."
    ),
}


def guardian_ack(decision: str, is_drill: bool) -> str:
    return _message(GUARDIAN_ACK[decision], is_drill)


def detail_pending(is_drill: bool) -> str:
    return _message("HỏiCon đang chuẩn bị chi tiết. Trong lúc chờ, anh/chị gọi hỏi người thân trước nhé.", is_drill)


def reply_incident_closed(is_drill: bool) -> str:
    return _message(
        "Cảnh báo này đã đóng nên HỏiCon không nhận thêm trả lời. "
        "Nếu anh/chị vẫn lo, anh/chị gọi hỏi thăm người thân nhé.",
        is_drill,
    )
