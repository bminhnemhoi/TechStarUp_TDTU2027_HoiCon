# Kế hoạch Spec 036: Eval đầy đủ

**Mã**: `036-eval-full` · **ROADMAP**: `P2-15`, `P2-18` · **Làn**: B · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| I. Dừng an toàn | Không đụng Android; eval chỉ chấm đồ thị máy chủ |
| II. Riêng tư | Kịch bản hư cấu; `leak_pii` mở rộng sang cassette `recorded` trước khi ghi đĩa |
| III. LLM chỉ nâng | `lower_than_floor` ở mọi bước; đột biến (a) bỏ `raise_only` phải bị bắt |
| IV. Công khai AI | `missing_ai_disclosure` 100% là ngưỡng tuyệt đối |
| V. Hợp đồng trước | `eval_suite.v1.json` mới + khối `gate` tùy chọn trong `eval_report.v1.json`, fixture trước code |
| VII. Bằng chứng | verdict `pass/fail/provisional/blocked`; số cassette viết tay không bao giờ in như số M3 |
| VIII. Ít code | Dùng lại toàn bộ `hoicon.eval` của 030; chỉ thêm bộ nạp cassette theo bộ, khối `gate`, một bộ kiểm |

## 2. Quyết định

| # | Quyết định | Lý do | Phương án bỏ |
|---|---|---|---|
| D1 | `full` = toàn thư viện, không chọn tay | Thêm kịch bản là tự vào eval; không có chuyện "giấu" ca khó | Bộ chọn tay (dễ lệch, dễ chọn ca dễ) |
| D2 | Cassette tìm theo thứ tự `recorded/<bộ>/` → `full/` → `smoke/` | Một ca chỉ có một bản viết tay; `recorded` thắng khi có | Chép cassette smoke sang full (hai bản lệch nhau) |
| D3 | Khối `gate` là thuộc tính **tùy chọn** của `eval_report.v1` | Thêm tùy chọn không phá báo cáo cũ; không cần `v2` | `eval_report.v2.json` (phải sửa mọi nơi đọc) |
| D4 | `unsafe_advice` dựa trên danh sách mẫu + mẫu phủ định, dữ liệu ở JSON có ví dụ | Kiểm được trong CI, người duyệt đọc được; giới hạn ghi rõ | LLM-judge (B6 chờ Minh, tốn tiền, không tất định) |
| D5 | `stale` = so `prompt_versions` của cassette với front-matter prompt lúc chạy | Phát hiện "đổi prompt mà số vẫn xanh vì cassette cũ" | Băm cả nội dung prompt (đổi dấu cách cũng stale) |
| D6 | `--record` ghi vào thư mục riêng, không ghi đè `synthetic` | Giữ được bộ đối kháng viết tay (LLM thật hiếm khi trả lời xấu theo ý muốn) | Ghi đè |
| D7 | Tỷ lệ chính thức tính trên ca không `draft` và không `stale`; khi tập rỗng ⇒ `null`, không phải 0 | Không giả số khi chưa có ca được duyệt | Gộp hết |

## 3. Hợp đồng (phác thảo)

```json
// eval_suite.v1.json
{"required": ["suite","version","description","cases"], "additionalProperties": false,
 "properties": {"suite": {"enum": ["smoke","full","injection"]}, "version": {"const": 1},
   "description": {"type": "string", "maxLength": 400},
   "min_cases": {"type": "integer", "minimum": 1},
   "quotas": {"type": "object", "additionalProperties": false, "properties": {
     "benign_ratio_min": {"type": "number"}, "injection_min": {"type": "integer"},
     "per_scam_category_min": {"type": "integer"}, "per_region_ratio_min": {"type": "number"}}},
   "cases": {"type": "array", "uniqueItems": true, "minItems": 1,
     "items": {"type": "string", "pattern": "^[a-z0-9]+(_[a-z0-9]+)*_[0-9]{3}$"}}}}
// eval_report.v1.json — thêm properties.gate (không thêm vào required)
"gate": {"type": "object", "additionalProperties": false,
  "required": ["name","verdict","reasons","official_cases","provisional_cases","stale_cases","metrics_official"],
  "properties": {"name": {"const": "M3"}, "verdict": {"enum": ["pass","fail","provisional","blocked"]},
    "reasons": {"type": "array", "items": {"type": "string", "maxLength": 200}},
    "official_cases": {"type": "integer", "minimum": 0}, "provisional_cases": {"type": "integer", "minimum": 0},
    "stale_cases": {"type": "integer", "minimum": 0},
    "metrics_official": {"oneOf": [{"type": "null"}, {"$ref": "#/$defs/metrics"}]},
    "twin_pairs_both_correct": {"$ref": "#/$defs/rate"}}}
// case: thêm "stale": {"type": "boolean"}, "cassette_source": {"enum": ["synthetic","recorded"]} (tùy chọn)
```

Tệp lược đồ được viết ở giai đoạn 0 (checkout chính, cùng commit với spec). Test hợp đồng trong `tests/contract/` là task B.

## 4. Bản đồ file

| Làn | File | Thay đổi |
|---|---|---|
| chung | `docs/schemas/eval_suite.v1.json`, `eval_report.v1.json` (khối `gate`), fixtures | mới / sửa (giai đoạn 0, đã làm) |
| B | `tests/contract/test_eval_schemas.py` (+ `eval_suite`, `gate`) | sửa |
| B | `data/scenarios/*.yaml` (+ ≥ 40), `backend/tests/contract/test_scenarios.py` | mới / sửa |
| B | `backend/eval/suites/{full,injection}.v1.json`, `backend/eval/cassettes/full/*.json`, `backend/eval/lexicon/unsafe_advice.vi.json` | mới |
| B | `hoicon/eval/{cases,replay,checks,report,cli,runner}.py` | sửa (bộ nạp theo bộ, `stale`, `unsafe_advice`, `gate`, `--record`) |
| B | `tests/unit/test_eval_suites.py`, `test_eval_unsafe_advice.py`, `tests/integration/test_eval_full.py`, `test_eval_mutations.py` | mới |
| B | `backend/eval/baseline-full.json`, `baseline-injection.json` | mới (`--write-baseline`) |
| B | `.github/workflows/backend.yml` | sửa |
| docs | `docs/AGENTS.md`, `.claude/skills/run-eval/SKILL.md`, `backend/README.md`, `backend/eval/README.md` (PROMPT-LOG) | sửa / mới |

## 5. Tái sử dụng

| Có sẵn (030) | Dùng để |
|---|---|
| `eval/cases.py::load_suite`, `build_event`, `case_secrets` | nạp mọi bộ; khóa bí mật cho `leak_pii` |
| `eval/replay.py::ReplayClient` | thêm tham số thư mục tìm cassette, không viết client mới |
| `eval/checks.py::evaluate` | thêm `unsafe_advice` vào danh sách, giữ chữ ký |
| `eval/report.py::compute_metrics`, `absolute_failures`, `compare` | tính lại trên tập chính thức cho `gate` |
| `domain/pii.py::mask_text` | kiểm cassette `recorded` |
| Skill `add-scam-scenario`, `vietnamese-scam-redteam` | soạn ca mới, ca chèn lệnh |

## 6. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Đọc nhầm số rào thành số M3 trong thuyết minh | **Cao** | Dòng cảnh báo đầu Markdown; verdict; `pitch-sync` đối chiếu `gate.verdict` |
| Kịch bản mới bịa nguồn | TB | `source_ref` phải mở được; test cấm URL rỗng; Minh duyệt (005) |
| `full` chậm trên CI | TB | Đo SC-002; FR-014 chạy theo đường dẫn nếu > 180 s |
| `unsafe_advice` báo nhầm câu an toàn ("đừng chuyển tiền") | TB | Mẫu phủ định + ví dụ âm trong test |
| P0-08 trễ ⇒ M3 chỉ có `provisional` | **Cao** | Ghi BLOCKED; báo Minh sớm: M3 cần khóa API trước ~26/12 để còn thời gian ghi cassette |

## 7. Rà soát `/speckit-analyze` (18/10/2026, vòng 1)

Phủ FR: 15/15 có task. **0 CRITICAL, 1 HIGH (đã sửa), 2 MEDIUM, 1 LOW.**

| # | Mức | Phát hiện | Xử lý |
|---|---|---|---|
| E1 | HIGH | Đột biến "bỏ bọc `<untrusted>`" không đo được bằng phát lại (cassette không phụ thuộc prompt) ⇒ SC-004 sẽ không bao giờ đạt | Thay bằng đột biến "giữ lời kể thô thay `note_flags`" (bắt bằng `leak_pii`); ghi rõ `<untrusted>` thuộc phần LLM thật (FR-013) |
| E2 | MEDIUM | `stale` dựa vào số phiên bản ⇒ sửa prompt mà giữ `@N` thì lách được | T009 thêm test ghim sha thân prompt theo phiên bản |
| E3 | MEDIUM | Thời gian `full` trên CI chưa biết ⇒ FR-014 có hai nhánh | SC-002 đo ở T012/T013; nhánh chạy theo đường dẫn nếu > 180 s |
| E4 | LOW | Cassette chỉ có khóa `risk_scorer`/`intervention`; prompt `case_file` (031) không có cassette | Eval không đi nhánh `case_file` (031 FR-003) ⇒ không ảnh hưởng; ghi lại để 031 không kỳ vọng eval kiểm hồ sơ |
