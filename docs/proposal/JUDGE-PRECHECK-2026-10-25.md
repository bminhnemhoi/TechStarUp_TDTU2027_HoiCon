# Chấm thử sơ bộ Vòng 1 (tác tử `judge`, 25/10/2026)

Bản text trích từ PDF đã nộp, đối chiếu repo @ 7222b3c. Tiêu chí: thể lệ mục 5.1 (`docs/competition/The_le_Tech_Startup_Challenger_2027.pdf`, tr.3);
thang 1–10 do `judge` tự đặt (thể lệ không có thang). **Chấm chính thức lại 10/11** sau khi Minh sửa (P1-04). Đề xuất sửa: `PITCH-SYNC-2026-10-25.md` A–J.

## Điểm ước lượng ≈ 74/110 (sửa 5 điểm yếu ⇒ ≈ 7,5/10)

| Tiêu chí | Điểm | Căn cứ |
|---|---|---|
| Tính mới, sáng tạo | 8 | Chuỗi "đang nghe số lạ → mở app ngân hàng" + kéo gia đình vào; đã có dự án cùng chủ đề (CallPeace, Guardian) |
| Tính khả thi | 6 | Code có thật; nhưng "đội 5 người", "50–100 gia đình" lệch thực tế (2 người, 0 gia đình) |
| Phù hợp thị trường | 7 | TAM/SAM có công thức; hệ số 1,5 / 12% / 60% là giả định chưa kiểm |
| Tiềm năng | 7 | B2B2C + CSR; phép tính hoàn vốn cho ngân hàng thuyết phục |
| Sự cần thiết | 9 | Số liệu có nguồn [1]–[12], vụ việc 9/2026 |
| Khả thi sản xuất – kinh doanh | 5 | B2B2C 64% doanh thu 2029 nhưng 0 LOI; cố vấn "[Đang liên hệ]"; mức sẵn lòng chi trả chưa kiểm |
| Độc đáo so với sản phẩm hiện có | 8 | Bảng 15 so sánh tốt |
| Kế hoạch tài chính | 6 | 3 kịch bản; chi phí 6.000 (§3.7) lệch 6.900 (Bảng 26); vốn góp theo 5 người |
| Truyền thông | 8 | "Mật khẩu gia đình", gian "Bạn có cứu được bà không?" |
| Kết quả dự kiến | 6 | 0 ⇒ 15.000 gia đình năm 2027; "phát hiện ≥ 90%" chưa có số đo mô hình |
| Hình thức đúng quy định | 4 | Còn `[Điền tên đội]`, `[Họ và tên]`; font Times New Roman 14 chưa kiểm được trên bản text |
| Cộng điểm Agentic AI | +1 (rủi ro) | Kiến trúc thật (LangGraph interrupt, MCP `threat`, trace) nhưng Bảng 9 tuyên bố quá mức |

## 5 điểm yếu (theo ảnh hưởng) ⇒ đề xuất trong PITCH-SYNC
1. Đội ngũ + hình thức ⇒ B, #15. 2. Bảng 9 tuyên bố agentic quá mức ⇒ **G**. 3. Tính năng lệch (Hỏi con, giọng nói, Langfuse, gọi lại người
thân, MCP `zalo`) ⇒ **H**. 4. Không có dữ liệu sơ cấp (H1–H5, khảo sát) ⇒ **J**. 5. Tài chính, chỉ tiêu ⇒ **I** (+ D, E cho BMC, Bảng 21).

## 10 câu phản biện khó nhất (gợi ý trả lời chỉ bằng số có nguồn)
1. **Đội 2 người làm nổi Android + web + 5 tác tử?** Tiến độ spec ở `docs/MASTER-PLAN.md`, `docs/ROADMAP.md`; quy trình đặc tả – kiểm thử –
   rà soát. Bền vững đội / người kinh doanh: *chưa có bằng chứng*.
2. **Agentic thật hay luồng cố định?** Interrupt `ask_elder`/`await_guardian`/`await_case_approval`, `recover()` sau sập, MCP `threat`
   (`docs/AGENTS.md`). Nói thẳng: xác minh tất định có chủ ý (không bịa nguồn).
3. **Tỷ lệ phát hiện / báo nhầm?** 110 ca (37 hợp lệ, 17 chèn lệnh, 48 đối kháng — `specs/036-eval-full/evidence.md`) nhưng cassette tổng hợp,
   kịch bản `draft`. Năng lực mô hình: *chưa có bằng chứng* (SC-007 BLOCKED).
4. **Đo máy thật chưa?** Máy ảo, bản release: p95 1.205 ms (API 36), 847 ms (API 34) (`specs/010-design-system/evidence.md`). Máy thật:
   *chưa có* (`specs/001-safe-pause-real-device`, BLOCKED).
5. **Người cao tuổi có cấp quyền "dữ liệu sử dụng" không?** *Chưa có bằng chứng* (H4).
6. **Con cái có trả 49.000 đồng/tháng?** *Chưa có bằng chứng* (H3; P1-02 đang dở).
7. **Cha mẹ dùng iPhone / kẻ gian bảo tắt app?** Thuyết minh thừa nhận iOS một phần (rủi ro #2); heartbeat báo "mất bảo vệ" (032). Tỷ lệ
   Android: *chưa có bằng chứng* (H2).
8. **Giới hạn Zalo 3 bot × 50 người, 3.000 tin/tháng?** Chuyển OA khi có pháp nhân; máy chủ đo với Zalo giả lập (`specs/023-guardian-alert`).
   Zalo thật: *chưa có* (`specs/002-zalo-guardian-channel`, BLOCKED).
9. **Con không trả lời? Báo nhầm gây phiền?** Hẹn giờ T1 nhắc → T2 người giám hộ thứ hai → T3 kết thúc (`docs/AGENTS.md`). "≤ 1 báo nhầm/tuần":
   *chưa có bằng chứng*.
10. **Dữ liệu ở đâu, ai chịu trách nhiệm khi bỏ sót?** Sổ đồng ý chỉ ghi thêm; rút đồng ý và xóa dữ liệu ngay trong app, có 24 giờ hủy được
    (specs 011, 038). Máy chủ đặt tại Việt Nam: *chưa có* (012 T010 BLOCKED).

## Kịch bản video — đã sửa theo nhận xét
Ba câu quá mức (01:20, 01:45, 02:20), thêm 15 giây đội + mô hình doanh thu, thống nhất ngày thí điểm — xem `VIDEO-V1-SCRIPT.md` mục cuối.
Còn yếu (người quyết): toàn màn hình máy ảo, không có người thật trong khung.
