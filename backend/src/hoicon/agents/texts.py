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


# ADR-012 / spec 024 FR-011: tóm tắt gửi người giám hộ chỉ ghép từ các câu cố định này (LLM chỉ chọn mã).
# Không chữ số/link; `{alias}` = cách xưng hô người cao tuổi.
# Thêm tình huống = thêm mã (guardian_brief.v2.json) + câu + điều kiện + test.
BRIEF_POINT_VI: dict[str, str] = {
    "unknown_call_then_finance_app": "Vừa rồi {alias} nghe một số lạ gọi rồi mở ứng dụng ngân hàng hoặc ví điện tử.",
    "sideloaded_app": "Vừa rồi {alias} mở một ứng dụng không tải từ cửa hàng CH Play, sau cuộc gọi lạ.",
    "call_still_ongoing": "Cuộc gọi lạ với {alias} có thể vẫn đang diễn ra.",
    "flagged_number": "Số điện thoại này nằm trong danh sách số bị báo nghi lừa đảo.",
    "caller_claims_authority": "{alias} cho biết người gọi xưng là công an, ngân hàng hoặc cơ quan nhà nước.",
    "asked_transfer_or_code": "{alias} cho biết người gọi bảo chuyển tiền hoặc đọc mã xác thực.",
    "asked_secrecy": "{alias} cho biết người gọi dặn giữ kín, đừng kể với ai.",
    "asked_install_app": "{alias} cho biết người gọi bảo cài ứng dụng hoặc mở một đường dẫn lạ.",
    "elder_unsure_of_caller": "{alias} cho biết chưa rõ người gọi là ai.",
    "common_scam_pattern": "Những điểm trên thường gặp trong các cuộc gọi giả danh để lừa chuyển tiền.",
    "may_be_routine": "Cũng có thể đây chỉ là việc bình thường, anh/chị cứ nhẹ nhàng hỏi thăm {alias} xem chuyện gì.",
}


def brief_summary(alias: str, points: list[str]) -> str:
    """Ghép câu cố định theo thứ tự điểm; mã không có câu bị bỏ (không bao giờ nhận chữ từ ngoài)."""
    sentences = (BRIEF_POINT_VI[p].replace("{alias}", alias) for p in points if p in BRIEF_POINT_VI)
    return " ".join(s[:1].upper() + s[1:] for s in sentences)  # alias là tên riêng/danh xưng ("bác Hùng") đứng đầu câu


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


# --- Hồ sơ vụ việc (spec 031): câu cố định cho `content` của `case_files` (không chữ số dài, link, tên thật).
CASE_FILE_AI_LABEL = (
    "Đây là trợ lý AI HỏiCon. Hồ sơ này do trợ lý AI soạn từ dữ kiện đã ghi; anh/chị đọc kỹ trước khi duyệt."
)
TRANSITION_VI: dict[str, str] = {
    "detected": "Điện thoại phát hiện dấu hiệu rủi ro",
    "assessing": "HỏiCon bắt đầu đánh giá mức rủi ro",
    "awaiting_guardian": "HỏiCon báo người giám hộ và chờ quyết định",
    "verifying": "HỏiCon tra cứu số điện thoại và đường dẫn",
    "rescore": "HỏiCon đánh giá lại sau khi tra cứu",
    "case_open": "Người giám hộ chọn: nghi lừa đảo, HỏiCon giữ hồ sơ mở",
    "closed": "Hồ sơ được đóng",
    "resolved_safe": "Người giám hộ xác nhận an toàn",
    "resolved_prevented": "Đã ngăn chặn được",
    "resolved_false_alarm": "HỏiCon ghi nhận đây là báo động nhầm",
    "resolved_no_response": "Chưa nhận được phản hồi từ người nhà",
}
RULE_VI: dict[str, str] = {
    "R1": "Đang nghe số lạ thì mở ứng dụng ngân hàng hoặc ví điện tử",
    "R2": "Cài hoặc mở ứng dụng ngoài cửa hàng CH Play sau cuộc gọi lạ",
}
RULE_DEFAULT_VI = "Điện thoại phát hiện dấu hiệu đáng ngờ và bật cảnh báo"
CASE_REASON_VI: dict[str, str] = {
    "flagged": "Số gọi tới nằm trong danh sách số bị báo nghi lừa đảo của HỏiCon",
    "authority": "Người gọi xưng là cơ quan nhà nước, công an hoặc ngân hàng",
    "transfer": "Người gọi yêu cầu chuyển tiền hoặc đọc mã xác thực (OTP)",
    "unknown_caller": "Người cao tuổi cho biết không biết người gọi là ai",
    "sideloaded": "Ứng dụng được mở không tải từ cửa hàng CH Play",
    "floor": "Mức rủi ro do luật trên điện thoại xác định",
}
ANSWER_VI: dict[str, str] = {"yes": "Có", "no": "Không", "unsure": "Chưa chắc", "timeout": "Chưa trả lời"}
CASE_LOCAL_FIELDS: list[dict[str, str]] = [
    {"key": "caller_phone", "label": "Số điện thoại đã gọi tới"},
    {"key": "account_number", "label": "Số tài khoản đã chuyển (nếu có)"},
    {"key": "amount", "label": "Số tiền đã chuyển (nếu có)"},
    {"key": "transfer_time", "label": "Giờ chuyển tiền (nếu có)"},
    {"key": "bank_name", "label": "Ngân hàng (nếu có)"},
]
VERIFICATION_SOURCE_DEFAULT = "Danh sách cảnh báo HỏiCon"


def guardian_case_file(alias: str) -> str:
    """Tin Zalo báo đã có bản nháp hồ sơ (spec 031 FR-006). Không có liên kết/token: nhắn "4" để lấy liên kết
    đăng nhập web (spec 027). Sự cố diễn tập không bao giờ có hồ sơ nên không có nhãn diễn tập."""
    return _message(
        f"HỏiCon đã soạn sẵn bản nháp hồ sơ vụ việc của {alias} để anh/chị mang đi trình báo nếu muốn. "
        "HỏiCon không tự gửi "
        "cho cơ quan nào. Anh/chị nhắn số 4 để nhận liên kết đăng nhập, rồi mở hồ sơ trên web để đọc và duyệt.",
        False,
    )


def case_file_summary(alias: str, app_category: str, level: str, authority: bool, transfer: bool) -> str:
    """Đoạn tóm tắt dựng từ mẫu (không LLM): dùng khi không có khóa API hoặc đoạn LLM bị bộ lọc loại."""
    app = APP_KIND_VI.get(app_category)
    parts = [f"{alias} nghe một cuộc gọi lạ" + (f" rồi mở ứng dụng {app}." if app else ".")]
    if authority and transfer:
        parts.append(
            "Người gọi xưng là cơ quan nhà nước, công an hoặc ngân hàng, và yêu cầu chuyển tiền hoặc đọc mã xác thực."
        )
    elif authority:
        parts.append("Người gọi xưng là cơ quan nhà nước, công an hoặc ngân hàng.")
    elif transfer:
        parts.append("Người gọi yêu cầu chuyển tiền hoặc đọc mã xác thực.")
    shown = RiskLevel(level) if level in {x.value for x in RiskLevel} else RiskLevel.HIGH
    parts.append(
        f"HỏiCon đánh giá mức rủi ro: {LEVEL_VI[shown].lower()}. HỏiCon đã nhắc {alias} tạm dừng và báo người giám hộ."
    )
    return " ".join(parts)


# --- Coach hằng tuần + báo "mất bảo vệ" (spec 032): mẫu cố định, không LLM. Người đọc là người giám hộ, chuyện nói về
# người cao tuổi ⇒ nói điều ĐÃ BIẾT, nguyên nhân CÓ THỂ (không khẳng định), MỘT việc nên làm; không hoảng sợ, không "bị
# hack", không khẳng định "an toàn" (máy không được bảo vệ thì "không thấy gì" không có nghĩa là không có gì).
DIGEST_OFF_COMMAND = "TẮT TIN TUẦN"
DIGEST_ON_COMMAND = "BẬT TIN TUẦN"


def round_coverage(coverage: float) -> int:
    """Độ phủ làm tròn tới 5% (không nói số lẻ giả chính xác)."""
    return round(max(0.0, min(1.0, coverage)) * 20) * 5


def guardian_protection_silent(alias: str, since_label: str) -> str:
    """`since_label`: mốc giờ Việt Nam đã định dạng ("07:30 ngày 20 tháng 10")."""
    return _message(
        f"Điện thoại của {alias} chưa báo về HỏiCon từ {since_label}. Có thể máy hết pin, đang tắt, mất mạng hoặc "
        f"hệ thống đã tắt ứng dụng chạy nền. Anh/chị nên gọi hỏi thăm {alias}, "
        f"hoặc nhờ {alias} mở ứng dụng HỏiCon trên điện thoại.",
        False,
    )


def guardian_protection_permission_off(alias: str) -> str:
    return _message(
        f"Trên điện thoại của {alias}, quyền để HỏiCon nhắc dừng lại khi có cuộc gọi lạ đang bị tắt, "
        f"nên lúc này HỏiCon chưa nhắc được. Anh/chị nên gọi hỏi thăm {alias}, "
        f"hoặc nhờ {alias} mở HỏiCon và bật lại quyền.",
        False,
    )


def weekly_digest(
    alias: str, incidents: int, resolved: int, coverage: float | None, drills: int, tip: str | None
) -> str:
    """Bản tin tuần (chiều Chủ nhật). `incidents`: số lần nhắc dừng lại của sự cố THẬT trong tuần; `resolved`: số lần
    đã có người nhà xử lý; `coverage`: độ phủ heartbeat 7 ngày hoặc None ("chưa đủ dữ liệu")."""
    lines = [f"Bản tin tuần của {alias}."]
    if incidents > 0:
        lines.append(
            f"Tuần qua HỏiCon đã nhắc {alias} dừng lại {incidents} lần, "
            f"trong đó {resolved} lần đã có người nhà xử lý xong."
        )
    elif coverage is None:
        lines.append(
            f"Tuần này HỏiCon chưa đủ dữ liệu về điện thoại của {alias} (máy chưa báo về đủ lâu), nên chưa thể nói gì."
        )
    else:
        lines.append(f"Tuần này HỏiCon không thấy dấu hiệu đáng ngờ nào trên điện thoại của {alias}.")
    if coverage is not None:
        lines.append(
            f"HỏiCon chạy trên điện thoại của {alias} khoảng {round_coverage(coverage)}% thời gian trong tuần."
        )
    elif incidents > 0:
        lines.append(f"HỏiCon chưa đủ dữ liệu để nói máy của {alias} được bảo vệ bao nhiêu phần tuần này.")
    lines.append(
        f"{alias} đã làm {drills} bài luyện tập nhận biết lừa đảo."
        if drills
        else f"{alias} chưa làm bài luyện tập nào."
    )
    if tip:
        lines.append(f"Mẹo tuần này: {tip}")
    lines.append(f"Nhắn {DIGEST_OFF_COMMAND} để ngừng nhận bản tin này.")
    return _message("\n".join(lines), False)


def digest_off_ack() -> str:
    return _message(
        "Đã tắt bản tin tuần cho anh/chị. HỏiCon vẫn nhận cảnh báo khi có chuyện và nhắn cho anh/chị ngay. "
        f"Muốn nhận lại bản tin, nhắn {DIGEST_ON_COMMAND}.",
        False,
    )


def digest_on_ack() -> str:
    return _message(
        "Đã bật lại bản tin tuần cho anh/chị. Bản tin đến vào chiều Chủ nhật hằng tuần. "
        f"Muốn ngừng, nhắn {DIGEST_OFF_COMMAND}.",
        False,
    )
