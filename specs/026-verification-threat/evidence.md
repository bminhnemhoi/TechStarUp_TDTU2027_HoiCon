# Bằng chứng nghiệm thu Spec 026: Tác tử xác minh, tra cứu E10 & danh sách đe dọa trên máy

- **Trạng thái (18/10/2026)**: Làn B (server, T001–T019) và Làn A (Android, T020–T027) đã xong và đã gộp vào `tien-collab-dev`;
  18/10 Làn A được đối chiếu lại với mã, hoàn thiện (màn đồng ý hiện đủ câu đã băm, sửa 2 vòng review UX) và đo trên AVD
  `hc-api36` nối backend thật (mục "Làn A Android" bên dưới). Giai đoạn Z: T028 đã chạy cả `hc-api36` và `hc-api34`; T029–T031
  chưa làm.
- **Số đo Làn B (máy dev, Postgres 15432, không phải máy thật)**:
  - `pytest` toàn bộ 1501 passed; `ruff check` và `ruff format --check` sạch; `check-spec-trace` 17 spec, 0 lỗi.
  - `hoicon-eval --suite smoke --compare baseline --shared-db-ok`: 20 ca, recall 100%, báo nhầm 0%, vi phạm 0, công khai
    AI 100%, lệch baseline +0,0 điểm %.
  - `POST /v1/lookups` p95 ≈ 14 ms (n = 50, trong tiến trình, `test_lookup_latency_p95`); 25 request đồng thời ⇒ đúng 20
    lọt; `GET /v1/threat-list` 24 lượt/ngày/thiết bị rồi 429.
  - Migration `0007` lên/xuống/lên ổn trên DB dev (kể cả khi sổ đồng ý đã có dòng `lookups`).
- **ADR-011** (bucket k-ẩn danh): ~~Đề xuất, chờ Tiến chấp nhận~~ → **Chấp nhận 18/10/2026** (Tiến; ghi vào ADR và commit 22/10/2026). ADR-006 có dòng "Sửa đổi bởi ADR-011".
- **Môi trường dự kiến**:
  - Linux CachyOS, Postgres dev trên Docker (cổng 15432), uvicorn trên localhost.
  - AVD `hc-api36` và `hc-api34` (`sdk_gphone64`).
  - Android build bằng JBR của Android Studio.
- **Nguồn số**: máy dev và máy ảo; máy ảo ≠ máy thật. Chưa có số đo trên máy thật vì Play Console/Firebase (P0-08) còn
  chặn.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 độ trễ tra cứu | API p95 ≤ 300 ms (n ≥ 50); E10 bấm → kết quả p95 ≤ 2 s (AVD 36) | `test_api_lookups.py` (đo thời gian) + log mốc `lookup_tapped` → `lookup_result` trên AVD (T026) | API: xem trên. E10 trên AVD nối backend thật: n = 10 lần, 504–521 ms (cả 10 lần ≤ 2 s). Mất mạng (bucket trên máy): 5–17 ms (n = 5). **Lưu ý:** 10/10 lần cùng ≈ 505 ms, đều một cách đáng ngờ; chưa tìm ra nguồn của "sàn" 500 ms (không thấy `delay`/`sleep` ở app hay ở đường `/v1/lookups`), nên đây là số máy ảo, không dùng làm cam kết | ĐẠT (máy ảo) |
| SC-002 riêng tư | 0 SĐT thô / h1 / URL trong DB, jobs, `agent_steps`, log; `threat-list` chỉ có bucket; chỉ lưu `bucket_enc`; ≥ 80 số/bucket ở b = 22 | quét DB + `caplog` (T013, T015, T018) + phép tính ở plan D1 + `security-privacy-reviewer` (T030) | chưa chạy | CHƯA ĐO |
| SC-003 kết luận & nâng mức | bảng plan §4 đúng 100%; phone không `safe`; mức không giảm, ≥ `rule_floor`; eval smoke ≥ baseline, 0 vi phạm, công khai AI 100% | `test_verification_rules.py`, `test_graph_verification.py`, `test_incident_service.py`, `hoicon-eval smoke --compare baseline` | chưa chạy | CHƯA ĐO |
| SC-004 ngoại tuyến | tra bucket p99 ≤ 5 ms / 100.000 bucket; đồng bộ lần 2 ⇒ 304; khớp nhầm trong ±30% của `N/2^b` | `:rules:test` (T020), `test_threat_list.py` (T015), E2E `fake_police` API 36 + 34 (T028) | `:rules:test` 81 test xanh (p99 ≈ 0,00025 ms); đồng bộ thật trên AVD: lần đầu 200, lần sau `since=` 304, bản mới 200. `fake_police` hc-api36: 10/10 hiện SafePause (phát hiện p50/p95 354/488 ms, SafePause p50/p95 508/614 ms). Số **chỉ có trong danh sách đồng bộ từ máy chủ** (không nằm trong h1 cứng của bản debug) cho SafePause "Rất cần cẩn thận" (CRITICAL) và máy chủ ghi `R1 critical`. hc-api34 (mã cuối): `fake_police` 10/10, SafePause p50/p95 674/725 ms ⇒ ĐẠT (lần chạy đầu sau khi khởi động có 1 lần UI-tree trượt, chạy lại đạt); chưa lặp kiểm "số chỉ có trong danh sách" trên hc-api34 | ĐẠT (máy ảo) |
| SC-005 E10 | 10 ảnh (5 trạng thái × 100%/200%); ≥ 20sp, ≥ 64dp, ≥ 7:1, công khai AI được đọc to; reviewer không còn mục chặn | ảnh ở `~/hoicon-evidence/026-verification-threat/` + `ux-elder-reviewer` (T026) | 10 ảnh trạng thái (nguy hiểm, cảnh báo, chưa có thông tin, mất mạng có/không trong danh sách × 100%/200%) + đồng ý ×2 + nhập ×3 ở `w1/`, chụp trên backend thật; `ux-elder-reviewer` lượt 2: **0 High**; 2 Medium đã sửa và chụp lại; còn 5 Low (bên dưới). Ảnh "an toàn" chỉ là bản xem trước (ảnh cũ ở `shots/`). Chưa đo tương phản trên ảnh, chưa thử TalkBack/giọng đọc thật | ĐẠT (máy ảo) |
| SC-006 chống lạm dụng | 429 đúng ngưỡng (kể cả 25 request đồng thời ⇒ 20 lọt); 403 khi chưa đồng ý; 404 nhà khác; ≤ 1 tin bằng chứng/sự cố; `threat-list` ≤ 24/ngày | `test_api_lookups.py`, `test_threat_list.py`, `test_graph_verification.py` | chưa chạy | CHƯA ĐO |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 scripts/check-spec-trace.py` (sau khi tạo bộ spec) | xem báo cáo phiên 16/10/2026 |

## Review độc lập

`security-privacy-reviewer` (server, 16/10/2026): 0 Critical, 0 High, 6 Medium, 8 Low. Đã sửa (test đỏ trước):
- #1 parser URL lệch trình duyệt (`\`, userinfo, `.apk` trong truy vấn); #2 khóa job `evidence` giờ theo `verification_id`;
- #4 dựng ảnh chụp: single-flight + giải mã ngoài event loop; #8 thiết bị chỉ gắn tra cứu vào sự cố CỦA mình;
- #10 lỗi 5xx của `threat-list` không tốn lượt ngày; #11 node `verification` không gọi `raise_level` với mức `none`.

Để lại, cần Tiến quyết (đã ghi ở ADR-011 / DATA-MODEL / API):
- #3 job xóa theo hạn + xóa khi rút đồng ý `lookups` (nợ P2-20); #5/#6 k-ẩn danh chỉ là ước tính, khóa `bucket_enc` dùng
  chung `HOICON_DATA_KEY` với `chat_id` (cân nhắc khóa riêng/HKDF); #7 người giám hộ chưa có đường ghi đồng ý `lookups`
  (403, spec 023/027); #9 `HOICON_ENV` mặc định `dev`; #12–#14 (last3 do client khai, thiếu `is_drill`/vết kiểm toán
  `raise_level`, vài CHECK/chỉ mục `(family_id, at)`).
- Lỗ hổng còn lại của #2: lần tra `dangerous` ĐẦU TIÊN rơi vào lúc đồ thị chưa tới `await_guardian` vẫn có thể không
  sinh tin `evidence` nếu không có lần tra nguy hiểm sau đó.

`ux-elder-reviewer` cho E10 đã chạy 2 lượt ở Làn A (xem mục "Làn A Android"); lượt đọc lại của reviewer cho các sửa của làn B vẫn chưa có.

## Làn A Android (T020–T027, đối chiếu và hoàn thiện 18/10/2026)

Đối chiếu từng task với mã thật rồi chạy lệnh Verify của task đó; chỉ tick khi xanh. Cổng cuối: `:rules:test` 81 + `:app:testDebugUnitTest` 248
test, 0 lỗi; `:app:lintDebug`, `:app:assembleDebug` xanh; `gitleaks dir --config .gitleaks.toml apps/android specs` sạch.

| Task | Mã | Verify đã chạy |
|---|---|---|
| T020 | `rules/.../ThreatBucketIndex.kt` + `ThreatBucketIndexTest` | `:rules:test` xanh (81) |
| T021 | Room v2, `Migration(1,2)`, `schemas/…/2.json`, `SentinelMigrationTest` (androidTest) | unit xanh + `:app:connectedDebugAndroidTest` trên hc-api36: 1/1 (outbox còn nguyên sau 1→2) |
| T022 | `ThreatSyncer`, `ThreatSyncWorker`, `LocalLists.isFlagged` dùng chỉ mục | unit xanh; đồng bộ thật trên AVD 200 → 304 → 200 |
| T023 | `LookupApiClient`, `UrlSanitizer` | unit xanh (`LookupApiClientTest`…) |
| T024 | mục đích `lookups`: chuỗi, hash ghim, màn đồng ý đúng lúc | unit xanh; **sửa 18/10:** `lookups_consent_summary` ("…có thể báo cho con bác biết") được băm vào sổ nhưng KHÔNG hiện trên màn (reviewer đánh High); nay hiện, kèm `LookupDisclosureTest` (mọi chuỗi `lookups_consent_*` của `ConsentTexts` phải có trên màn; đã thử đột biến: bỏ dòng ⇒ test đỏ) |
| T025 | `LookupScreen`/`LookupResultScreen`/`LookupActivity` + nút ở E6 | `:app:testDebugUnitTest :app:lintDebug :app:assembleDebug` xanh |
| T026 | ảnh E10 100%/200% + reviewer | ≥ 10 ảnh ở `w1/`; reviewer lượt 2 không còn High |
| T027 | `VietQrParser`, Google Code Scanner 16.1.0, "Dán đường link" | unit xanh; `grep -c "android.permission.CAMERA"` manifest = 0 |

**Sửa theo review UX (lượt 1 → 2):** màn nhập không tự mở bàn phím (tiêu đề, hướng dẫn, "Quay lại" thấy ngay ở 200%); nút Dán/Quét vào
phần cuộn; bàn phím số; ô nhập ≥ 64dp, nhãn gắn vào ô cho TalkBack; chỉ câu "Đây là trợ lý AI HỏiCon." in đậm và đứng đầu,
phần "Kết quả chỉ để tham khảo…" xuống sau câu hành động; câu hành động rút gọn, ghi "(OTP)"; bỏ câu phủ định lồng nhau
("chưa có trong danh sách không có nghĩa là an toàn") bằng câu khẳng định; nhãn nút canh giữa.
**Còn lại (Low, để theo dõi):** tiêu đề chồng đồng hồ khi cuộn với bàn phím mở; "kiểm tra lại khi có mạng" không có nút riêng;
câu phản hồi sau "Hỏi con" chưa chụp; lý do máy chủ có thể còn chữ "OTP" trần (làn B); ảnh "an toàn" cần chụp lại trước khi bật;
màn nhập không đọc to.

**Chưa kiểm:** quét QR thật (máy ảo không quét được; chỉ có test JVM); TalkBack/giọng đọc; hc-api29; máy thật;
phần cuộn của màn đồng ý (thẻ 2–3); màn lỗi/hết lượt.

## Review bảo mật lượt 2 — T029/T030 (18/10/2026, nhánh `feat/w1-server`)

- **T029** `bash scripts/gen-api-client.sh && pnpm --dir apps/web typecheck`: client sinh lại sạch (sau khi thêm mã 503 của
  `threat-list` vào OpenAPI), typecheck xanh. `docs/API.md`, `DATA-MODEL.md`, `AGENTS.md`, `DESIGN-SYSTEM.md` đã có nội dung 026 từ trước;
  `API.md` được cập nhật cho 3 thay đổi dưới đây. Chưa sửa `DATA-MODEL.md` §6 (còn dòng cũ "chưa có job retention" — ngoài quyền của lượt này).
- **T030** `security-privacy-reviewer` đọc mã server 026 (chỉ đọc, không chạy test): **0 Critical, 0 High, 3 Medium, 14 Low**.
  8 mục đối chiếu đều ĐẠT: PII (không số thô/h1/URL trong DB/log/job/trace), `bucket_enc` (nonce ngẫu nhiên mỗi lần, AAD gắn `value_hmac`),
  đồng ý `lookups` đọc DB mỗi lần, IDOR, nâng mức chỉ qua `raise_level`, MCP `threat` (Caddy chặn `/mcp*`).
- **Đã sửa 3 Medium (test viết cùng lúc):**
  - **#1 dò danh sách đe dọa qua `/v1/lookups`**: thêm trần cuộn 30 ngày — thiết bị 600, người giám hộ 600, cả gia đình 3.000 (dòng
    `actor = system` không tính). Ngưỡng là con số tôi chọn (≈ 10 lần cách dùng thật), **Tiến cần xác nhận**. Chưa giới hạn theo IP:
    Caddy chuẩn không có `rate_limit`. Phản hồi vẫn có `confidence` và tên nguồn (đổi cần đổi hợp đồng `docs/schemas`, ngoài quyền).
  - **#2 giải mã `bucket_enc` hỏng**: hỏng toàn bộ, hoặc ≥ 3 dòng và > 5% ⇒ `threat-list` trả 503, không đệm, không tốn lượt ngày
    (trước đó phát ảnh chụp RỖNG hợp lệ, máy sẽ thay danh sách tốt bằng nó). Vài dòng lẻ vẫn chỉ bị bỏ qua.
  - **#3 rút đồng ý `lookups`**: trong cùng giao dịch ghi sổ đồng ý, các lượt tra cứu của thiết bị người đó mất `subject_hmac` (64 số 0),
    `last3`, `sources`, `list_version`; GIỮ dòng để làm sổ đếm hạn mức (xóa hẳn thì rút rồi cấp lại thành cách đặt lại hạn mức).
- **Kết quả test:** `test_api_lookups.py` + `test_threat_list.py` 104 passed (mới: 4 trần 30 ngày, 4 làm sạch khi rút đồng ý,
  11 ngưỡng giải mã + 3 qua endpoint). Hạn mức giờ/ngày hiện có vẫn xanh.
- **14 Low để lại** (ghi lại để Tiến quyết, không sửa trong lượt này): k-ẩn danh chỉ đúng với dải di động (#4); `bucket_bits` 23–24 làm k
  tụt dưới 80 mà không cảnh báo (#5); `bucket_enc` dùng chung khóa với `chat_id` (#6); người giám hộ dùng chung trần gia đình 200/ngày (#7);
  yêu cầu bị từ chối không tính hạn mức (#8); hạn mức `threat-list` đếm trong bộ nhớ (#9); máy chủ chưa kiểm (phiên bản, sha256) văn bản đồng ý (#10);
  `verifications` thiếu `is_drill` và chỉ mục `(family_id, at)` (#11); `.gitignore` chưa chặn tệp seed thật có h1 (#12); tài liệu cũ (#13);
  `unflag` chưa xóa đệm 5 phút (#14); heuristic URL `thue`/`%252E` (#15); đường người giám hộ chết vì chưa có đường ghi đồng ý (#16);
  số `0912345678` trong test (#17).
- **ADR-011:** reviewer đánh giá, **không chấp nhận hộ** (chờ Tiến). Điều kiện đề nghị nếu chấp nhận: ghi rõ k chỉ cho dải di động, guardrail
  `bucket_bits`, tách khóa/HKDF, trần 30 ngày (đã làm), cập nhật DPIA (đã làm ở spec 011).
- Chưa có reviewer đọc lại các bản sửa trên. T031 (bộ kiểm đủ, gồm Android + máy ảo) vẫn thuộc người tích hợp.

## Còn mở (không đánh ☑)

- Số đo trên máy thật cho E10 và cho `onScreenCall` với bucket.
- Sổ đăng ký tên miền/tổng đài chính thức: nguồn để kết luận `safe`. Cần dữ liệu đã kiểm và Minh duyệt.
- Tra cứu số tài khoản (`kind=account`): chưa có nguồn dữ liệu.
- Trạng thái `verifying`/`rescore` chưa được dùng; phải sửa `decided_state` trước.
