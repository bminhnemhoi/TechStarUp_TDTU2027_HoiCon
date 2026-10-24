// Diễn tập của người giám hộ (spec 028 FR-011): chữ hiển thị cho mã trạng thái và mã từ chối của `DrillService`.
// 3 kịch bản v1 trùng `data/drills/*.yaml` (có test `test_web_drill_scripts_match_data` kiểm id + tên).
export const DRILL_SCRIPTS: { id: string; title: string }[] = [
  { id: "drill_bank_card_locked", title: "Cuộc gọi báo thẻ bị khóa" },
  { id: "drill_police_safe_account", title: "Cuộc gọi từ 'điều tra viên'" },
  { id: "drill_relative_urgent_money", title: "Cuộc gọi 'cháu cần tiền gấp'" },
];

export const DRILL_DURATIONS = [
  { minutes: 30, label: "30 phút" },
  { minutes: 60, label: "1 giờ" },
  { minutes: 120, label: "2 giờ" },
  { minutes: 240, label: "4 giờ" },
];

export const DRILL_STATUS_VI: Record<string, { icon: string; text: string }> = {
  scheduled: { icon: "◔", text: "Đã đặt lịch" },
  offered: { icon: "☎", text: "Đã mời, chờ người nhận làm" },
  in_progress: { icon: "▶", text: "Đang làm" },
  passed: { icon: "✓", text: "Đã hoàn thành bài" },
  failed: { icon: "!", text: "Còn vài bước chưa chắc. Anh/chị có thể trò chuyện nhẹ nhàng với người thân" },
  aborted: { icon: "■", text: "Dừng giữa chừng" },
  declined: { icon: "✕", text: "Lần này người thân chưa muốn làm. Không sao, anh/chị có thể đặt lại lúc khác" },
  expired: { icon: "○", text: "Hết giờ, chưa làm" },
};

// Mã `DrillRefused` ⇒ câu cụ thể, có việc nên làm (không lộ mã kỹ thuật).
export const DRILL_REFUSAL_VI: Record<string, string> = {
  consent_missing: "Người nhận chưa đồng ý tham gia diễn tập. Anh/chị nhờ người đó bật lựa chọn diễn tập trong ứng dụng HỏiCon.",
  member_not_found: "Không tìm thấy người nhận trong gia đình. Anh/chị chọn lại người nhận.",
  monthly_limit: "Gia đình đã đặt đủ số bài diễn tập trong tháng này. Anh/chị đặt lại vào tháng sau.",
  script_not_approved: "Kịch bản này chưa được duyệt để dùng. Anh/chị chọn kịch bản khác.",
  script_unknown: "Không tìm thấy kịch bản này. Anh/chị chọn lại kịch bản.",
  window_invalid: "Giờ bắt đầu và kết thúc chưa hợp lý. Anh/chị chọn lại giờ.",
  window_overlaps: "Người này đã có một bài diễn tập trong khoảng giờ này. Anh/chị chọn giờ khác.",
  window_past: "Khoảng giờ này đã qua. Anh/chị chọn một giờ sau bây giờ.",
  window_too_long: "Khoảng giờ dài quá (tối đa 4 giờ). Anh/chị chọn ngắn hơn.",
  window_too_short: "Khoảng giờ ngắn quá (tối thiểu 30 phút). Anh/chị chọn dài hơn.",
};
