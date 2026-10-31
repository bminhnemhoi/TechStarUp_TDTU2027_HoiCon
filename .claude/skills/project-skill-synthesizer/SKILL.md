---
name: project-skill-synthesizer
description: "Chuyên gia phân tích ngữ cảnh kho mã (codebase context) và tự động kiến tạo các kỹ năng nội bộ (Project-Scoped Skills) chỉ tồn tại trong dự án này. Kích hoạt khi: người dùng muốn tạo thêm kỹ năng mới cho dự án, tối ưu hóa quy trình làm việc đặc thù của repo, hoặc khi phát hiện một tác vụ lặp đi lặp lại cần được chuẩn hóa cho mọi AI agent (Claude Code, Opus, Sonnet, Antigravity, Codex) cùng đọc và áp dụng."
---

# Project Skill Synthesizer (Kiến Trúc Sư Kỹ Năng Nội Bộ Dự Án)

Kỹ năng này trao cho AI khả năng **tự học và tự mở rộng năng lực** cho riêng dự án hiện tại, tạo ra các kỹ năng chuyên biệt (custom skills) được lưu trữ ngay trong `.claude/skills/`.

---

## 1. Nguyên Tắc Cốt Tử Khi Tạo Kỹ Năng Nội Bộ (Project-Scoped Doctrine)

1. **Ranh Giới Bất Xâm Phạm (Isolation)**:
   - Kỹ năng được tạo ra **CHỈ NẰM TRONG REPO NÀY** (`.claude/skills/<skill-name>/SKILL.md`).
   - Tuyệt đối không lưu vào thư mục toàn cục của máy (`~/.gemini/` hay `~/.claude/`) để tránh làm ô nhiễm môi trường của các dự án khác.
2. **Đa Agent Tương Thích (Multi-Agent Universality)**:
   - Mọi Agent hoạt động trong dự án (Claude Code / Opus / Sonnet / Codex / Gemini Antigravity) đều đọc được cấu trúc `.claude/skills/` theo chuẩn chung.
3. **Kỷ Luật Thực Tiễn (Actionable, No Fluff)**:
   - Kỹ năng phải có lệnh kiểm chứng thực tế (test command), bảng đối chiếu, mẫu phân cảnh hoặc quy trình từng bước rõ ràng, không được chỉ viết lý thuyết suông.

---

## 2. Quy Trình 4 Bước Tổng Hợp Kỹ Năng Mới

Khi User yêu cầu *"hãy tạo kỹ năng mới"* hoặc phát hiện nhu cầu phát triển:

### Bước 1: Quét Ngữ Cảnh Dự Án (Context Scan)
- Đọc `docs/ROADMAP.md` và `docs/MASTER-PLAN.md` để nắm các mốc việc đang chờ.
- Kiểm tra các file kiến trúc cốt lõi: `docs/ARCHITECTURE.md`, `docs/DATA-MODEL.md`, `CLAUDE.md`, `.specify/memory/constitution.md`.
- Quét cấu trúc thư mục để xác định công nghệ: Frontend (Next.js/React), Mobile (Android/Compose), Backend (FastAPI/Alembic).

### Bước 2: Xác Định Điểm Nghẽn & Đặt Tên Kỹ Năng
- Xác định điểm nghẽn: Kiểm thử lặp lại? Soạn thảo hồ sơ thi cử? Đo đạc hiệu năng máy ảo?
- Đặt tên theo dạng kebab-case ngắn gọn: `<chủ-đề>-<vai-trò>` (VD: `lat-m1-verifier`, `zalo-template-designer`, `compose-accessibility-audit`).

### Bước 3: Soạn Thảo `SKILL.md` Chuẩn Điểm 10
Cấu trúc bắt buộc của file `.claude/skills/<tên-kỹ-năng>/SKILL.md`:
```markdown
---
name: <tên-kỹ-năng>
description: "<Mô tả súc tích: Kỹ năng làm gì, giải quyết vấn đề gì, khi nào kích hoạt và trigger keywords>"
---

# <Tên Đầy Đủ Của Kỹ Năng>

## 1. Mục Đích & Bối Cảnh Trong Dự Án
[Nêu rõ liên hệ với task nào trong docs/ROADMAP.md hoặc tài liệu kiến trúc nào]

## 2. Quy Trình Từng Bước (Step-by-Step Workflow)
[Các bước thực thi tuần tự, kèm lệnh kiểm chứng cụ thể]

## 3. Tiêu Chuẩn Đầu Ra (Acceptance Criteria & Output Template)
[Mẫu bảng biểu, cấu trúc file hoặc định dạng kết quả bắt buộc]
```

### Bước 4: Kiểm Chứng & Thông Báo Cho Tổng Tư Lệnh
- Kiểm tra cú pháp Markdown và đảm bảo đường dẫn file chính xác.
- Báo cáo cho User: Tên kỹ năng, file vị trí, cách kích hoạt và giá trị mang lại cho dự án.
