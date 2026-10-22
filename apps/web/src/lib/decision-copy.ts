import type { Decision } from "@/lib/client";

// Câu xác nhận và câu đã ghi nhận của quyết định người giám hộ (spec 027); dùng chung trang chi tiết và `/sim` (spec 033).
export const DRILL_DONE =
  "[DIỄN TẬP] Đã ghi nhận. Đây chỉ là bài tập, không có nguy hiểm thật. Cảm ơn anh/chị đã tham gia.";

/** Câu hỏi xác nhận và câu đã ghi nhận; diễn tập không bao giờ nói như sự cố thật (luật 8). */
export function decisionCopy(decision: Decision, name: string, isDrill: boolean): { ask: string; done: string } {
  const tag = isDrill ? "[DIỄN TẬP] " : "";
  switch (decision) {
    case "safe":
      return {
        ask: `${tag}Anh/chị đã nói chuyện trực tiếp với ${name} và chắc chắn ${name} an toàn? HỏiCon sẽ đóng cảnh báo này.`,
        done: isDrill ? DRILL_DONE : `Đã ghi nhận: ${name} an toàn. HỏiCon đóng cảnh báo này.`,
      };
    case "emergency_pause":
      return {
        ask: `${tag}Anh/chị nghi ${name} đang bị lừa? HỏiCon sẽ giữ cảnh báo mở để theo dõi.`,
        done: isDrill
          ? DRILL_DONE
          : `Đã ghi nhận: nghi lừa đảo. HỏiCon giữ cảnh báo mở để theo dõi và không tự báo cho cơ quan nào. Anh/chị hãy gọi ngay cho ${name}, nhắc tuyệt đối không chuyển tiền.`,
      };
    case "false_alarm":
      return {
        ask: `${tag}Anh/chị xác nhận đây là HỏiCon báo nhầm?`,
        done: isDrill ? DRILL_DONE : "Đã ghi nhận: HỏiCon báo nhầm. Cảm ơn anh/chị đã cho biết.",
      };
  }
}
