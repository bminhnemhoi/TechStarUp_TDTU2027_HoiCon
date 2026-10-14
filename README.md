# HỏiCon — Hỏi con trước khi chuyển tiền

**Trợ lý Agentic AI chống lừa đảo cho cả nhà.** Dự thi *Tech Startup Challenger 2027* (Khoa CNTT – Đại học Tôn Đức Thắng).

Kẻ gian thường giữ máy người cao tuổi trong cuộc gọi và hối thúc chuyển tiền trong vài phút. HỏiCon can thiệp đúng
khoảnh khắc đó:

1. **Lính gác (Android)** nhận ra chuỗi hành vi rủi ro — *đang nghe số lạ → mở app ngân hàng* — bằng luật tất định
   ngay trên máy, rồi bật **khoảng dừng an toàn** có giọng nói tiếng Việt trong ≤ 3 giây, kể cả khi mất mạng.
2. **5 tác tử AI** trên máy chủ (LangGraph + MCP) chấm rủi ro, hỏi lại người cao tuổi, **báo con cháu qua Zalo**,
   xác minh số/link, lập hồ sơ vụ việc và huấn luyện cả nhà bằng các buổi diễn tập.

> **Người mới / người làm tiếp: đọc [`docs/HANDOFF.md`](docs/HANDOFF.md) trước** — trạng thái, cách dựng môi trường,
> quy trình, kế hoạch từng tuần tới Vòng 1, tài khoản, rủi ro.

## Trạng thái (14/10/2026)

**Phase 1 — spike kỹ thuật + hồ sơ Vòng 1.** Gate G0 đã đạt. Ước tính ≈ 15% tổng thể, ≈ 30% hồ sơ Vòng 1.

| Phần | Trạng thái |
|---|---|
| Cảm biến Android: số lạ → app ngân hàng → màn dừng an toàn (P1-S1) | ✅ cơ chế chốt trên máy ảo ([ADR-007](docs/adr/ADR-007-co-che-cam-bien-android.md)); ⏳ số đo máy thật |
| Dừng an toàn với app ngân hàng, `:demobank`, bộ đo `:latency` (P1-S2) | ✅ [ADR-008](docs/adr/ADR-008-dung-an-toan-va-app-ngan-hang.md); ⏳ Firebase Test Lab |
| Lõi tác tử LangGraph + hẹn giờ + cổng LLM + MCP `threat` (P1-S4) | ✅ [ADR-009](docs/adr/ADR-009-loi-tac-tu.md), 86 test; ⏳ khóa API để chọn model |
| 60 kịch bản lừa đảo cho eval (P1-07) | 📝 bản nháp chờ duyệt |
| Zalo Bot (P1-S3), giọng nói (P1-S5), thuyết minh, video, khảo sát | ⏳ kế hoạch: [HANDOFF §5](docs/HANDOFF.md#5-kế-hoạch-tiếp-theo) |

Lộ trình đầy đủ, mã task và gate: [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Nguyên tắc riêng tư

- Không đọc SMS, nhật ký cuộc gọi, danh bạ hay nội dung cuộc gọi; không dùng Accessibility.
- Số điện thoại chỉ rời máy dưới dạng băm; máy chủ lưu HMAC có pepper ([ADR-006](docs/adr/ADR-006-bam-hmac-so-dien-thoai.md)).
- Đường dừng an toàn không dùng mạng hay LLM; LLM chỉ được **nâng** mức rủi ro, không bao giờ hạ.
- Mọi tin nhắn trong sự cố mở đầu bằng "Đây là trợ lý AI HỏiCon"; sổ đồng ý chỉ ghi thêm.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `apps/android/` | App "Lính gác" — Kotlin, Compose; module `:app`, `:rules` (luật tất định, JVM thuần), `:demobank` (app ngân hàng mẫu để demo), `:latency` (bộ đo độ trễ cho Firebase Test Lab) |
| `backend/` | FastAPI + SQLAlchemy/Alembic + LangGraph (checkpoint Postgres) + MCP SDK + Anthropic SDK (Python 3.12, `uv`) |
| `apps/web/` | Next.js — trang hành động cho người giám hộ, trace tác tử, eval, gian trưng bày |
| `infra/` | Docker Compose (Postgres 17 + pgvector) |
| `data/` | Danh sách app tài chính, kịch bản lừa đảo (eval/diễn tập), dữ liệu demo hư cấu |
| `docs/` | Bàn giao, lộ trình, kiến trúc, mô hình dữ liệu, ADR, báo cáo spike, hợp đồng sự kiện, thuyết minh dự thi, nghiên cứu |
| `scripts/` | Dựng máy ảo Android, kịch bản mô phỏng cuộc gọi, sinh client API |
| `.claude/` | Harness Claude Code: hook bảo vệ quyền riêng tư, subagent chuyên gia, skill ([`docs/HARNESS.md`](docs/HARNESS.md)) |

## Chạy thử (Windows + Git Bash)

```bash
pnpm install                                   # task runner + web
uv sync --directory backend                    # backend
pnpm dev:all                                   # Postgres :15432 → migration → API :18000 + web :3100
pnpm test                                      # test hook + backend + typecheck web
apps/android/gradlew -p apps/android :rules:test :app:assembleDebug
uv run --directory backend python -m hoicon.agents.spike demo   # một sự cố đầu–cuối của tác tử
```

Hướng dẫn đầy đủ từ máy trắng: [`docs/HANDOFF.md` §3](docs/HANDOFF.md#3-ngày-đầu-tiên-dựng-môi-trường).

Môi trường Android (JDK 21, SDK, máy ảo `hc-api36/34/29`): [`docs/EMULATOR.md`](docs/EMULATOR.md).

## Tài liệu chính

[**Bàn giao**](docs/HANDOFF.md) · [Lộ trình](docs/ROADMAP.md) · [Kiến trúc](docs/ARCHITECTURE.md) · [Mô hình dữ liệu](docs/DATA-MODEL.md) · [ADR](docs/adr/) · [Báo cáo spike](docs/spikes/) ·
[Hợp đồng sự kiện](docs/schemas/risk_event.v1.json) · [Chính sách Play](docs/PLAY-POLICY.md) ·
[Thuyết minh dự thi](docs/proposal/HoiCon_Ban_mo_ta_y_tuong_TSC2027.pdf)

---
Tác giả: [@bminhnemhoi](https://github.com/bminhnemhoi) (TDTU) · đồng phát triển: [@Towfienes](https://github.com/Towfienes).
Bản quyền thuộc tác giả — chưa cấp giấy phép mã nguồn mở.
