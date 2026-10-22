# Bằng chứng nghiệm thu Spec 012: Hạ tầng VPS (làn B)

- **Trạng thái**: hạ tầng đã dựng và thử trên máy dev (17–18/10/2026), review bảo mật độc lập xong và đã sửa Medium. **Chưa chạy trên
  VPS thật**: Let's Encrypt thật, tên miền, bot Zalo thật, chép sao lưu ra ngoài máy và phần Android (làn A) đều BLOCKED.
- **Spec viết ngược** sau khi hạ tầng có (commit `29bd228`); các sửa sau review nằm ở nhánh `feat/w1-server`.
- **Môi trường**: Linux CachyOS, Docker Compose 5.6, stack thử trong project compose riêng `hoicon-prodtest2` (tên miền `hoicon.localhost`,
  chứng chỉ nội bộ của Caddy, khóa GIẢ sinh bằng `openssl`), Postgres dev `hoicon-db` không bị đụng tới.
- **Nguồn số**: máy dev, một lần đo mỗi mục; thời gian build/khôi phục không đại diện cho VPS. Chưa chạy: CI trên PR, Windows, VPS thật.

## Kết quả theo tiêu chí

| Tiêu chí | Ngưỡng | Cách đo | Kết quả | Trạng thái |
|---|---|---|---|---|
| SC-001 triển khai một lệnh | `/readyz` qua Caddy = 200, `zalo_mode: live`, `/login` = 200; lần hai lũy đẳng | `scripts/deploy-vps.sh` chạy 6 lần (DB trống, DB có dữ liệu, sau mỗi sửa) | Mọi lần xanh: `{"status":"ok","db":"up","zalo_mode":"live"}`, `/login` 200, `/docs` `/redoc` `/openapi.json` `/mcp/threat/` 404. Lần đầu (build lạnh) 1 phút 42 giây; lần chạy lại có sao lưu trước migrate 11 giây; migration 0001 → 0010 | ĐẠT (máy dev) |
| SC-002 cô lập | Postgres 0 cổng ra host, không ra Internet; web không tới backend/Postgres/Internet; backend uid ≠ 0, rootfs chỉ đọc; khóa sao lưu ∉ container | `docker port`, kết nối thử từ trong container, `touch`, liệt kê tên biến, `test_deploy_vps.py` | Postgres: không cổng, không ra Internet. Web: `EAI_AGAIN` khi tới `backend`/`postgres`, `ENETUNREACH` khi ra Internet. Backend: uid 10001, ghi `/app` bị từ chối, ra Internet được; 0 biến `BACKUP_KEY` trong container | ĐẠT |
| SC-003 đóng cửa | `/mcp/*`, `/docs`, `/redoc`, `/openapi.json` ⇒ 404; reviewer không lách được | 33 biến thể tự thử (hoa/thường, `//`, `%2f`, `%6d`, `..`, `%2e%2e`, `;`) + reviewer thử ≈ 35 biến thể khác (kể cả HTTP/3 suy luận) | Tất cả 404 ở Caddy hoặc rơi vào web (Next 404), không biến thể nào tới backend. Reviewer: ĐẠT | ĐẠT |
| SC-004 SSE không đệm | Sự kiện tới đúng nhịp phát | upstream giả phát 4 sự kiện cách 0,5 s qua Caddy | +8 / +508 / +1008 / +1508 ms, `X-Accel-Buffering: no`, không nén. **Chỉ với upstream giả**; backend thật mới thử tới 401 không token | MỘT PHẦN |
| SC-005 nhật ký sạch | 0 token/cookie/khóa trong log truy cập **và** log lỗi Caddy | yêu cầu thật có `Cookie`/`Authorization`/`Referer`, lỗi 502 cố ý, `//login/<token>` | 0 lần lộ sau sửa. Trước sửa: `Refresh: 0;url=/login/<token>` của Next lọt vào log (đã bỏ `Refresh`/`Content-Location`) | ĐẠT |
| SC-006 thất bại an toàn | Thiếu/sai biến, `/readyz` không 200, backend unhealthy, migrate hỏng, Caddyfile hỏng ⇒ thoát 1 kèm hướng dẫn, không "XONG"; sao lưu hỏng ⇒ không migrate | 5 ca hỏng cố ý | Cả 5 thoát mã 1, 0 dòng "XONG". Caddyfile hỏng: `caddy reload` lỗi, Caddy vẫn phục vụ cấu hình cũ (`/readyz` 200). Sao lưu hỏng (chọn nhầm Postgres): script dừng trước migrate | ĐẠT |
| SC-007 sao lưu → khôi phục | Tệp mã hóa 0600; `restore-check` khớp manifest + trigger bất biến | `backup-vps.sh` rồi `restore-check` trên Postgres của stack prod | Tệp 70.007 byte, 24 bảng, 12 dòng khớp manifest, trigger `ALWAYS` còn nguyên, DB tạm đã xóa; khôi phục 0,48 s (tổng 0,72 s) trên dữ liệu rất nhỏ | ĐẠT (máy dev) |
| SC-008 VPS thật | Let's Encrypt thật, `https://<tên miền>/healthz` 200, đo build/khôi phục | — | Chưa có VPS/tên miền | BLOCKED |
| SC-009 Android phát hành | AAB lên Play internal testing; đo khởi động nguội | — | Làn A; Play Console (W0-3) | BLOCKED |

## Lệnh đã chạy

| Lệnh | Kết quả |
|---|---|
| `python3 -m unittest discover -s scripts/tests -p test_deploy_vps.py` | 26 test OK (6 kiểm biến, 11 bất biến compose, 9 Caddyfile) |
| Đột biến hạ tầng (`compose.prod.yml`, `Caddyfile`, `deploy-vps.sh`) | 19/19 làm test đỏ; tệp khôi phục nguyên vẹn sau mỗi lần |
| `shellcheck -x -P SCRIPTDIR` trên 4 script | sạch |
| `caddy validate` + `caddy fmt --diff` trong ảnh `caddy:2.10.2-alpine` | `Valid configuration`, đúng định dạng |
| `docker build` backend (463 MB, 59 s), web (1,4 GB, 64 s) | xanh; chạy `--read-only --cap-drop ALL` import được app, nạp 3 kịch bản diễn tập, `alembic heads` = 0010 |
| Ma trận 4 ca hỏng + Caddyfile hỏng | xem SC-006 |
| `uv run --directory backend pytest` | 2059 passed, 21 skipped (role `hoicon_app` đã có sẵn trên DB dev nên `test_db_roles.py` tự bỏ qua) |

## Review độc lập (`security-privacy-reviewer`, 18/10/2026)

**0 Critical, 0 High, 2 Medium, 12 Low.** Đã chạy Caddy/uvicorn thật với bộ lọc log thật; không đọc `.env`. Kết luận 10 mục: 1, 2, 3, 4, 7, 9
(kích thước thân) ĐẠT; 5 ĐẠT có điều kiện; 6 ĐẠT một phần; 8 lỗi nhẹ.

**Đã sửa:**
- **M-1** web cùng mạng với backend và backend tin `X-Forwarded-For` từ mọi nguồn ⇒ tách mạng `web` (`internal`) khỏi `api`; chỉ Caddy cùng mạng `api`
  với backend. Test: web không chung mạng với backend/Postgres, `api` = {backend, caddy}.
- **M-2** không timeout kết nối ⇒ `read_header 10s`, `read_body 30s`, `idle 2m`, tiêu đề ≤ 16 KB; RAM Caddy 128 → 192 MB.
- L-1 regex che token chịu `//login/…`; bỏ `Location`; L-3 bỏ khóa Gemini khỏi container; L-4 lỗi SQL không kèm câu lệnh trong log Postgres;
  L-6 `backup.sh` dùng `--frozen --no-dev`; L-7 khóa/bí mật chỉ ký tự an toàn (Compose cắt `$`, ` #`); L-8 deploy kiểm 404 cho `/docs /redoc /openapi.json /mcp/threat/`; L-11 bỏ `X-Powered-By`.

**Tìm thêm khi kiểm lại sau sửa (không thuộc báo cáo reviewer):**
- `Refresh: 0;url=/login/<token>` của Next lọt vào log Caddy khi gọi `//login/<token>` ⇒ bỏ `Refresh`, `Content-Location`.
- Cổng 80 do Caddy tự tạo **không nhận** `servers { timeouts }` (Slowloris không bị ngắt sau 25 s) ⇒ khai báo site `http://<tên miền>` tường minh; giờ ngắt đúng 10,0 s.
- Mount **từng tệp** Caddyfile giữ inode cũ sau `git pull` và deploy không nạp lại ⇒ mount thư mục + `caddy reload` trong deploy.

**Để lại (chưa sửa, cần quyết hoặc cần VPS thật):**
- **L-2** `/readyz` công khai và chạm DB mỗi lần gọi (theo yêu cầu giám sát bên ngoài; có thể đệm 5–10 giây hoặc chỉ mở `/healthz`).
- **L-5** ảnh ghim theo tag chứ không theo digest, Postgres chưa `cap_drop`, chưa `pids_limit`, Caddy chạy root (đã `cap_drop ALL`).
- **L-9** (suy luận) IPv6 + userland-proxy của Docker có thể gộp mọi khách IPv6 thành một IP ở giới hạn ghép đôi: kiểm trên VPS thật trước khi đặt bản ghi AAAA.
- **L-10** địa chỉ IP khách nằm trong log Caddy/uvicorn: DPIA chưa nêu mục đích và hạn lưu của log IP.
- **L-12** khóa sao lưu nằm cùng máy với bản sao lưu: chỉ có tác dụng khi bản sao được chép ra ngoài (BLOCKED T012).
- Chưa đặt `docs_url=None` khi `HOICON_ENV=prod` ở `main.py` (lớp phòng thủ thứ hai); Caddy đang là lớp duy nhất.
- Chưa có reviewer đọc lại các bản sửa trên.

## Còn mở (không đánh ☑)

T010–T015 trong `tasks.md`: VPS + DNS + Let's Encrypt thật; bot Zalo thật + `setWebhook`; bật `hoicon-backup.timer` và chép sao lưu ra ngoài máy;
áp `roles.sql` ở prod; giám sát `/readyz`; phần Android (`specs/029-pilot-kit/evidence.md`).

## Wave 3 (làn B)

- **T019 ĐẠT:** log Caddy ra stdout nên hạn giữ do driver Docker (`max-size 10m × max-file 5` mỗi dịch vụ, test `test_every_service_has_bounded_logs`);
  `roll_keep_for` chỉ dùng được khi ghi ra tệp nên KHÔNG áp dụng (lệch so với chữ của task, hạn theo dung lượng chứ không theo ngày — **cần Opus** nếu muốn hạn theo ngày).
  Đã ghi mục đích + hạn vào `docs/PRIVACY-DPIA.md` §2 và `docs/DATA-MODEL.md` §6. Verify: `unittest test_deploy_vps` 28 OK; `caddy validate` (`caddy:2.10.2-alpine`) Valid.
- **T017 BLOCKED:** role `hoicon_app` đã có sẵn trên DB dev với mật khẩu do người khác đặt; chạy API/worker dưới role này cần mật khẩu hoặc đặt lại mật khẩu (tôi không đổi).
  Tiến: cho phép đặt mật khẩu tạm hoặc tự chạy `HOICON_DATABASE_URL=<url hoicon_app> pytest tests/integration/test_db_roles.py`.
