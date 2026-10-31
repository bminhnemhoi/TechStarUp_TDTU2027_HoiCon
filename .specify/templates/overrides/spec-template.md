# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[feat/###-feature-name]`

**Created**: [DATE]

**Status**: Draft

**Input**: User description: "$ARGUMENTS"

<!--
  HỎICON (brownfield): spec này chỉ mô tả PHẦN CHÊNH LỆCH so với những gì đã có. Trỏ tới tài liệu sẵn có thay vì chép:
  docs/PRD.md (US-xx), docs/ROADMAP.md (mã task, gate), docs/adr/ (quyết định), docs/DATA-MODEL.md, docs/schemas/.
  Viết bằng tiếng Việt; định danh kỹ thuật bằng tiếng Anh. Số spec lấy từ docs/MASTER-PLAN.md §3, không tự đặt.
-->

## Truy vết *(mandatory)*

- **Mã ROADMAP**: [vd. P2-05, P2-06]
- **User story PRD**: [vd. US-02, US-04]
- **ADR liên quan**: [vd. ADR-001, ADR-007] — đổi quyết định đã chốt ⇒ cần ADR mới, ghi ở đây
- **Gate nghiệm thu**: [vd. M1 — tiêu chí nào trong ROADMAP]
- **Phụ thuộc spec**: [vd. 001 (số máy thật), 020 (hợp đồng ghép đôi)]
- **Làn**: [A = Android · B = backend/AI/web · A+B]

## User Scenarios & Testing *(mandatory)*

<!--
  User stories ưu tiên theo hành trình (P1 quan trọng nhất), mỗi story KIỂM THỬ ĐỘC LẬP được.
  Người dùng của HỏiCon: người được bảo vệ (≥ 60 tuổi, Android), người giám hộ (con cháu, Zalo), người vận hành/BGK.
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!-- Bắt buộc cân nhắc: mất mạng, app bị kill/khởi động nguội, Android 10 vs 16, cỡ chữ 200%, TalkBack,
     gửi trùng/idempotent, LLM quá hạn, hết hạn mức Zalo, dữ liệu diễn tập/demo, người dùng rút đồng ý. -->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

### Functional Requirements

<!-- Mỗi FR phải được ít nhất 1 task trong tasks.md nhắc tới bằng mã (check-spec-trace kiểm). -->

- **FR-001**: System MUST [specific capability]
- **FR-002**: System MUST [specific capability]

*Đánh dấu chỗ chưa rõ:* **FR-00X**: … [NEEDS CLARIFICATION: …]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents — trỏ bảng trong docs/DATA-MODEL.md nếu đã có]

## Bất biến an toàn *(mandatory — ghi "không đụng tới" nếu không liên quan)*

- **Dừng an toàn** (Hiến chương I): [ảnh hưởng tới đường găng? vẫn offline, ≤ 3 s, không chặn vĩnh viễn?]
- **LLM chỉ nâng** (III): [node nào gọi LLM, fallback mẫu nào, công cụ có tác dụng phụ nào]
- **Công khai AI** (IV): [tin/màn nào mới tới người cao tuổi hoặc Zalo]

## Quyền riêng tư & đồng ý *(mandatory)*

| Dữ liệu mới / thay đổi | Dạng lưu (băm/che/không lưu) | Mục đích đồng ý (enum) | Hạn lưu | Gửi LLM? |
|---|---|---|---|---|
| [vd. trạng thái quyền thiết bị] | [jsonb, không PII] | [vd. `device_health`] | [vd. 90 ngày] | [Không] |

Quyền Android mới: [không có / tên quyền + lý do + kiểm với docs/PLAY-POLICY.md]

## UX người cao tuổi *(mandatory nếu có màn hình hoặc câu chữ mới)*

- Màn hình: [vd. E7 SafePause, E9] — theo `docs/DESIGN-SYSTEM.md`
- ≤ 2 hành động chính · cỡ chữ 200% · tương phản ≥ 7:1 · tự đọc to? · TalkBack
- Câu chữ: [xưng "bác", không gây hoảng sợ, có hành động cụ thể]

## Success Criteria *(mandatory)*

### Measurable Outcomes

<!-- Ghi rõ MÔI TRƯỜNG ĐO cho mỗi số: máy ảo (AVD nào) / Firebase Test Lab (máy nào) / máy thật. -->

- **SC-001**: [Measurable metric] — đo trên: [môi trường], n = [số lần]
- **SC-002**: [Measurable metric] — đo trên: [môi trường]

## Kế hoạch bằng chứng *(mandatory)*

<!-- Những gì phải có trong specs/<spec>/evidence.md trước khi đánh ☑ trong ROADMAP. -->

- [vd. output `uv run --directory backend pytest` (số test)]
- [vd. `emu-scenario.py --scenario fake_police --runs 10` trên AVD 36 + 34: p50/p95]
- [vd. ảnh 100% + 200% + báo cáo `ux-elder-reviewer`]

## Ngoài phạm vi & mốc cắt

- Ngoài phạm vi: [những gì spec này KHÔNG làm]
- Nếu trễ, cắt trước: [phần nào, theo danh sách cắt ROADMAP]

## Assumptions

- [Assumption about target users / scope / environment / dependency]
