# Checklist tham chiếu cho `/speckit-checklist` (HỏiCon)

> `/speckit-checklist` sinh checklist **chất lượng yêu cầu** cho từng spec ("unit test cho câu chữ của spec"), không phải
> checklist code. Khi gọi, truyền tên một trong ba chủ đề dưới đây; checklist sinh ra phải bao các mục tương ứng (diễn đạt
> theo spec cụ thể). Mục nào không liên quan ghi "N/A — lý do".

## privacy — gọi khi spec đụng dữ liệu cá nhân, LLM, manifest, Zalo, đồng ý
- Spec liệt kê **mọi** trường dữ liệu mới, dạng lưu (băm/che/không lưu) và hạn lưu (`docs/DATA-MODEL.md` §6)?
- Có trường nào có thể chứa số điện thoại / số tài khoản / OTP / CCCD / tên thật / Zalo ID dạng thô? Spec nói rõ cách che?
- Mỗi mục đích dữ liệu mới có giá trị enum đồng ý + phiên bản văn bản? Rút đồng ý thì xảy ra gì?
- Dữ liệu gửi LLM đã nêu rõ, đi qua `llm_router` (che PII), nội dung kẻ gian bọc `<untrusted>`?
- Quyền Android mới (nếu có) có nằm trong danh sách cấm? Có giải trình Play (`docs/PLAY-POLICY.md`)?
- Tin Zalo / màn hình mới tới người cao tuổi có câu công khai "Đây là trợ lý AI HỏiCon"?
- Dữ liệu diễn tập/demo được gắn `is_drill`/`is_demo` và không lẫn vào số liệu thật?

## elder-ux — gọi khi spec có màn hình, thông báo, giọng đọc hoặc câu chữ mới
- Mỗi màn có ≤ 2 hành động chính, nút chính ≥ 24sp đậm, vùng chạm ≥ 64dp, chữ ≥ 20sp?
- Spec nêu hành vi ở cỡ chữ 200% và màn nhỏ 720×1280 (nút không trôi khỏi màn hình)?
- Màu rủi ro luôn đi kèm biểu tượng + chữ; tương phản ≥ 7:1; diễn tập có màu riêng?
- Màn quan trọng tự đọc to? Có hành vi khi TalkBack bật (thay thế cho thao tác giữ 3 giây)?
- Câu chữ xưng "bác", giọng ấm, không gây hoảng sợ, có hành động cụ thể tiếp theo?
- Trạng thái loading / rỗng / lỗi / mất mạng được mô tả?

## release-block — gọi khi spec đưa bản build tới người thật (thí điểm, closed testing, gian trưng bày)
- Đã có E3 công bố nổi bật + bản ghi đồng ý có phiên bản (P2-02)?
- Đã thay SharedPreferences bằng Room + Tink cho dữ liệu rủi ro (P2-05)?
- Bản phát hành dùng buildType release/demo, R8 bật, log chẩn đoán (`HC_TIMING`, `HcSpikeLog`) tắt (P1-08)?
- Phát hành qua Google Play (internal/closed testing), không gửi APK, không hướng dẫn bật tùy chọn nhà phát triển?
- Người dùng thí điểm ≥ 18 tuổi, có quy trình theo `docs/PILOT-PROTOCOL.md`?
- `privacy-audit` sạch và `security-privacy-reviewer` không còn finding High?
