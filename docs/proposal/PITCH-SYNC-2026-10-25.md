# Đối chiếu cam kết thuyết minh ↔ sản phẩm (pitch-sync, 25/10/2026)

Nguồn cam kết: `HoiCon_Ban_mo_ta_y_tuong_TSC2027.pdf` (bản đã nộp) và `src/build.js` (số dòng bên dưới).
Trạng thái thật: `tien-collab-dev` @ 4afb1b1, `docs/ROADMAP.md`, `specs/*/evidence.md`. Soạn bởi nhà điều phối (Opus) — **chưa sửa thuyết minh**:
theo skill `pitch-sync`, sửa chỉ khi Minh đồng ý; bản `.docx` đã được Minh sửa tay, dựng lại bằng pipeline sẽ mất các sửa đó (`src/README.md`),
và `convert.ps1` cần Microsoft Word trên Windows ⇒ **phần sửa + xuất bản là việc của Minh**.

## 1. Bảng đối chiếu

| # | Cam kết | Vị trí | Trạng thái thật | Bằng chứng | Hành động |
|---|---|---|---|---|---|
| 1 | 50–100 gia đình thí điểm (tới Vòng 2 và 27/02) | build.js 346, 412, 503; PDF tr.4 | **Lệch**: 0 gia đình; Play Console chưa đăng ký (W0-3); gate M3 ≥ 20, G3 ≥ 30 | ROADMAP gate; MASTER-PLAN §8 B4 | **Sửa câu chữ** (đề xuất A) — Minh quyết B4 |
| 2 | Đội 5 người, 3 thành viên CNTT; vốn góp 5 thành viên; 12 giờ/tuần/người | 502; PDF tr.~23, 26 | **Lệch**: đội 2 người (Minh, Tiến) + đội tác tử AI | CLAUDE.md, HANDOFF | **Sửa** (đề xuất B) — Minh quyết B5; nếu bổ sung người thật trước 13/11 thì điền tên |
| 3 | Nhóm khách hàng "sinh viên", "Chế độ sinh viên" (tính năng 5, gói Cơ bản) | PDF tr.1, 20; build.js bảng tính năng | **Chưa làm, ngoài MVP** (PRD chỉ người cao tuổi) | PRD US-01..10 | Ghi "mở rộng sau MVP (2027)" (B5) |
| 4 | "Mật khẩu gia đình" (tính năng 4, Cơ bản; chiến dịch §10.2) | bảng tính năng; 646 | **Chưa có tính năng**; chỉ là lời khuyên trong câu E7 | grep mã: chỉ `strings.xml` | Ghi là **chiến dịch truyền thông + lời khuyên trong app**, không phải tính năng MVP; hoặc thêm task (Minh) |
| 5 | Tin Zalo có nút [Gọi mẹ] [Xác minh] [Cho phép tiếp tục] | 466 | **Khác cách làm**: Zalo Bot trả lời số 1/2/3 + liên kết trang hành động `/a/[token]` (nút "Gọi điện", "Đã gọi được", "Nghi lừa đảo", "HỏiCon báo nhầm") | 023 evidence, DESIGN-SYSTEM web | Sửa câu: "tin Zalo kèm tóm tắt và đường dẫn tới trang hành động: Gọi mẹ · Nghi lừa đảo · Báo nhầm" |
| 6 | Diễn tập "hằng tuần"; kho kịch bản cập nhật "hằng tuần" | 460, 478, 593, 644, 646 | **Lệch**: diễn tập tối đa **2 bài/tháng** (PILOT-PROTOCOL, `MONTHLY_LIMIT = 2`); kịch bản cập nhật theo cảnh báo chính thức, không theo lịch | `drill_service.py` | Sửa "hằng tuần" ⇒ "định kỳ (tối đa 2 lần/tháng)"; bản tin Coach **hằng tuần** thì đúng (032) |
| 7 | Khoảng dừng an toàn tức thì | §3 | **Đạt (máy ảo)**: E7 ≤ 3 s, bản release p95 1,2 s (API 36), 10/10 (API 34) — **chưa đo máy thật** | 010 evidence T031/T033 | Ghi rõ "đo trên máy ảo; máy thật đo trong thí điểm" (luật: không tuyên bố số chưa đo) |
| 8 | 5 tác tử (Chấm rủi ro, Can thiệp, Xác minh, Hồ sơ vụ việc, Huấn luyện) | 342 | **Đạt (code)**: 024, 026, 031, 032; trace `/trace` | specs 024–033 | Giữ |
| 9 | Bộ đánh giá ≥ 100 kịch bản tiếng Việt; công bố tỷ lệ phát hiện/báo nhầm | 412, PDF tr.~16 | **Một phần**: 110 kịch bản + 17 injection; số hiện là **rào tất định (cassette synthetic)**, chưa phải số mô hình thật (M3); 110 kịch bản còn `draft` | 036 evidence; §8 mục 6, 11 | Không đưa số recall/báo nhầm vào thuyết minh Vòng 1; ghi "bộ 110 kịch bản đã dựng" |
| 10 | Mô hình AI: Gemini Flash / Claude Haiku / GPT mini; giọng nói Gemini Live | PDF tr.~22 | **Lệch một phần**: `llm_router` hiện chỉ Anthropic (Claude); chưa có khóa API (P0-08); giọng nói (004) đã code | AGENTS.md, 004 29/29 | Sửa: "định tuyến theo lớp mô hình (hiện dùng Claude; có thể thay nhà cung cấp)" |
| 11 | PostgreSQL, pgvector, **Redis** | PDF tr.~22 | **Lệch nhỏ**: không dùng Redis (hàng đợi job bằng Postgres, ADR-002) | ADR-002 | Bỏ "Redis" |
| 12 | Dữ liệu định danh lưu trên hạ tầng đặt tại Việt Nam | PDF tr.~17 | **Chưa có VPS** (012 T010 BLOCKED) | 012 evidence | Giữ cam kết; Tiến chọn VPS đặt tại VN |
| 13 | Không ghi âm, không đọc giao dịch, không Accessibility; đồng ý theo từng quyền, rút lại bất kỳ lúc nào | 381; PDF tr.~17 | **Đạt**: manifest cấm quyền; sổ đồng ý chỉ ghi thêm; rút từng mục + xóa dữ liệu từ app (038, xóa có 24 giờ hủy được) | 011, 034, 037, 038 | Giữ; có thể nêu "xóa dữ liệu từ app" |
| 14 | ≥ 300 phản hồi khảo sát; ≥ 1 LOI | 346 | **Chưa có số** (P1-02 Minh phát tán) | ROADMAP P1-02 | Người làm |
| 15 | Tên đội, họ tên thành viên | PDF tr.1, bảng nhân sự | **Còn chỗ trống** `[Điền tên đội]`, `[Họ và tên]` | PDF | Minh điền |

## 2. Đề xuất câu chữ (để Minh chép vào Word)

- **A (B4, thí điểm)** — thay "50–100 gia đình thí điểm": "**20–30 gia đình thí điểm** (người lớn ≥ 18 tuổi, có đồng ý), tuyển từ khảo sát
  Vòng 1; mở rộng 50–100 gia đình trong giai đoạn Tết 2027 nếu kết quả tốt." (khớp gate M3 ≥ 20, G3 ≥ 30).
- **B (B5, đội ngũ)** — thay "Đội 5 người với 3 thành viên CNTT…": "**Đội 2 thành viên** (Minh — sản phẩm, kinh doanh; Tiến — kỹ thuật)
  làm việc cùng **một đội tác tử AI lập trình** có quy trình đặc tả – kiểm thử – rà soát; có cố vấn chuyên môn." Cập nhật mục vốn góp và tỷ lệ
  sinh viên CNTT theo thể lệ (> 20% thành viên là sinh viên Khoa CNTT — kiểm lại với đội 2 người).
- **C (Zalo, #5)**, **D (diễn tập, #6)**, **E (mô hình/Redis, #10–11)**: như cột "Hành động".
- **F (số đo, #7, #9)**: chỉ dùng số có nguồn: "khoảng dừng an toàn hiện trong ≈ 1,2 giây (p95, bản phát hành, máy ảo Android 14 và 16)";
  không nêu recall/báo nhầm cho tới khi có số mô hình thật.

## 3. Việc của người (chặn nộp 13/11)
1. Minh quyết B4, B5 (MASTER-PLAN §8 mục 3) ⇒ chọn đề xuất A/B hoặc câu khác.
2. Minh sửa trong Word (bản đã sửa tay), xuất PDF bằng `convert.ps1` trên Windows, điền tên đội/thành viên.
3. P1-02 khảo sát ≥ 300 phản hồi; P1-03 quay video theo `docs/proposal/VIDEO-V1-SCRIPT.md`; P1-04 gọi `judge` chấm thử 10/11.
