# Triển khai HỏiCon lên VPS (spec 012, P2-04)

Hướng dẫn vận hành **một VPS chạy Docker**: Postgres + backend (API và worker trong một tiến trình, ADR-002) + web người
giám hộ + Caddy lo HTTPS. Tệp liên quan:

| Tệp | Việc |
|---|---|
| `infra/compose.prod.yml` | 4 dịch vụ: `postgres`, `backend`, `web`, `caddy` |
| `infra/caddy/Caddyfile` | HTTPS tự động, định tuyến, header bảo mật, SSE, che token trong nhật ký |
| `infra/env.prod.example` | Mẫu biến môi trường → sao chép thành `infra/.env.prod` |
| `backend/Dockerfile`, `apps/web/Dockerfile` | Ảnh backend (Python 3.12 + uv) và web (Next.js) |
| `scripts/deploy-vps.sh` | Kiểm biến → build → sao lưu → migrate → nạp container → kiểm `/readyz` |
| `scripts/backup-vps.sh` | Sao lưu mã hóa của prod (bọc `scripts/backup.sh`, xem `docs/setup/BACKUP.md`) |

```
Internet ──80/443──▶ caddy ──┬── /v1/*, /webhooks/zalo/*, /healthz, /readyz ──▶ backend :18000 ──▶ postgres :5432
                             └── còn lại (trang người giám hộ) ───────────────▶ web :3100          (mạng `db`, không ra Internet)
```
Chỉ Caddy có cổng ra ngoài (80, 443 TCP; 443 UDP cho HTTP/3). Backend và web không có `ports:`; Postgres nằm trên mạng
docker `internal: true` nên **không có cổng nào xuất ra máy chủ và cũng không có đường ra Internet**.

## 1. Chuẩn bị VPS

- **Cấu hình đề xuất:** 2 vCPU, 4 GB RAM, ≥ 40 GB ổ đĩa, Ubuntu 24.04 hoặc Debian 12. *Đây là đề xuất, chưa đo trên VPS
  thật.* Đo trên máy dev lúc rảnh: backend ≈ 160 MB, web ≈ 50 MB, Postgres ≈ 40 MB, Caddy ≈ 13 MB. Lần **build** là lúc ngốn
  RAM nhất (`next build`); VPS dưới 2 GB RAM nên thêm swap.
- **Phần mềm:** Docker Engine kèm plugin Compose ≥ 2.24, `git`, `curl`, `openssl`. Muốn sao lưu cần thêm `uv`
  (<https://docs.astral.sh/uv/>): công cụ sao lưu là Python chạy trên máy chủ.
- **DNS:** bản ghi A (và AAAA nếu có IPv6) của tên miền trỏ về VPS **trước khi** triển khai, nếu không Let's Encrypt không
  cấp được chứng chỉ. Web, API và webhook Zalo dùng chung một tên miền (ví dụ `app.hoicon.vn`).
- **Tường lửa:** chỉ mở 22 (SSH), 80, 443/tcp, 443/udp. Lưu ý Docker tự thêm quy tắc iptables cho cổng nó xuất ra và
  **bỏ qua `ufw`**; vì vậy compose chỉ xuất đúng 80/443 và không bao giờ xuất 5432.
- **Người dùng:** tạo người dùng riêng (không dùng root) và thêm vào nhóm `docker`. Nhóm `docker` tương đương quyền root
  trên máy chủ; chỉ người vận hành được vào.
- **Lấy mã:** `git clone` repo về, `git checkout` đúng nhánh/tag cần chạy. Script ghi mã phát hành là hash commit; bản có
  thay đổi chưa commit bị gắn `-dirty` và khó tái lập.

## 2. Bí mật: `infra/.env.prod`

```bash
cp infra/env.prod.example infra/.env.prod
chmod 600 infra/.env.prod          # script từ chối chạy nếu quyền khác 600/400
openssl rand -hex 32               # chạy MỖI LẦN cho một khóa: pepper, khóa dữ liệu, khóa sao lưu, khóa JWT
openssl rand -hex 24               # mật khẩu Postgres
```
Điền từng dòng, mỗi dòng dạng `TÊN=giá_trị` (không ghi chú cùng dòng). **Không dán giá trị vào chat, issue hay PR.**

- Bốn khóa (`HOICON_PHONE_PEPPER_1`, `HOICON_DATA_KEY_1`, `HOICON_BACKUP_KEY_1`, `HOICON_DEVICE_JWT_SECRET`) phải **khác
  nhau**; script từ chối giá trị trùng.
- **Mất khóa = mất dữ liệu liên quan:** mất pepper thì không so khớp lại được số điện thoại đã băm; mất khóa dữ liệu thì
  người giám hộ đã ghép phải ghép lại; mất khóa sao lưu thì mọi bản sao lưu thành vô dụng. Cất bản sao của **cả bốn khóa**
  ở nơi KHÁC với bản sao lưu dữ liệu (ví dụ trình quản lý mật khẩu của đội).
- `HOICON_ENV`, `HOICON_ZALO_MODE`, `HOICON_RUN_WORKER`, `HOICON_WEB_BASE_URL`, `HOICON_DATABASE_URL` do compose **ép
  cố định**; có ghi trong tệp cũng bị bỏ qua. Nhờ đó không thể vô tình chạy prod ở chế độ dev.
- Khóa sao lưu **không** được đưa vào container ứng dụng; chỉ `scripts/backup-vps.sh` đọc nó.

## 3. Triển khai

```bash
bash scripts/deploy-vps.sh --check   # chỉ kiểm biến + cấu hình compose, KHÔNG đổi gì
bash scripts/deploy-vps.sh           # triển khai thật
```
Thứ tự script làm, mỗi bước dừng ngay nếu lỗi:

1. Kiểm công cụ, quyền tệp biến, và **từng biến bắt buộc** (thiếu/sai định dạng/trùng khóa ⇒ in danh sách *tên biến*, không
   bao giờ in giá trị).
2. `docker compose build --pull` (ảnh gắn thẻ `hoicon-backend:<mã phát hành>`, `hoicon-web:<mã phát hành>`).
3. Khởi động Postgres, chờ healthy.
4. **Nếu DB đã có dữ liệu:** sao lưu mã hóa ngay (`backup-vps.sh`). Sao lưu thất bại ⇒ **không migrate**. Lần đầu (DB trống)
   bỏ qua bước này. `--skip-backup` chỉ dùng khi bạn đã tự sao lưu.
5. `alembic upgrade head` bằng ảnh mới, *trước khi* nạp container mới.
6. `docker compose up -d --wait`: chờ cả bốn dịch vụ healthy (backend healthy nghĩa là `/readyz` 200).
7. **Chỉ coi là xong khi** `https://<tên miền>/readyz` trả đúng HTTP 200 *qua Caddy* (thử tối đa 24 lần × 5 giây vì chứng
   chỉ lần đầu cần vài chục giây), `/login` (web) trả 200 và `/docs` trả 404.

Thất bại ở bước nào thì script in 40 dòng nhật ký backend gần nhất (đã bỏ dòng healthcheck) cùng gợi ý quay lui, rồi thoát
mã khác 0. Chạy lại script là an toàn (lũy đẳng).

Tùy chọn: `--env-file <tệp>`, `--skip-backup`, `--check-url <URL>`, `--insecure` (chứng chỉ tự ký, chỉ để thử cục bộ).

## 4. Kiểm sau triển khai

```bash
alias hc='docker compose -f infra/compose.prod.yml --env-file infra/.env.prod'
hc ps                                           # 4 dịch vụ (healthy)
curl -fsS https://<tên-miền>/readyz             # {"status":"ok","db":"up","zalo_mode":"live"}
curl -sI https://<tên-miền>/ | grep -iE 'strict-transport|content-security|x-frame|x-content'
curl -s -o /dev/null -w '%{http_code}\n' https://<tên-miền>/docs   # 404
```
`/readyz` 503 cho biết lý do mà không lộ giá trị: `{"missing":["phone_pepper",...]}` (thiếu khóa),
`{"misconfigured":["zalo_mode"]}` (prod mà Zalo đang mock) hoặc `{"db":"down"}`.

## 5. Đặt webhook Zalo

Webhook chỉ đặt được khi `https://<tên-miền>` đã chạy (Zalo gọi thử ngay khi đặt). Lệnh chạy **trong container backend**
(đã có token và bí mật), chỉ in Đạt/Lỗi và không bao giờ in token hay URL:
```bash
hc exec backend python -m hoicon.ops.zalo_webhook set --url https://<tên-miền>
hc exec backend python -m hoicon.ops.zalo_webhook info
```
`HOICON_ZALO_WEBHOOK_SECRET` trong tệp biến phải chính là bí mật mà Zalo sẽ gửi lại ở header `X-Bot-Api-Secret-Token`.

## 6. Nhật ký và quyền riêng tư

- Nhật ký docker xoay vòng (10 MB × 5 tệp mỗi dịch vụ). Xem: `hc logs -f --tail=100 backend`.
- **Caddy che token trong nhật ký** (cả nhật ký truy cập lẫn nhật ký *lỗi*): `/login/<token>`, `/a/<token>` và
  `/v1/action/<token>` ghi thành `.../REDACTED`; bỏ hẳn các tiêu đề `Cookie`, `Authorization`, `X-Bot-Api-Secret-Token`,
  `Referer` và `Set-Cookie`. Đã thử bằng yêu cầu thật và bằng lỗi 502 (xem mục 11).
- Địa chỉ IP khách vẫn có trong nhật ký truy cập (cần để điều tra lạm dụng). Nếu DPIA yêu cầu che, thêm bộ lọc `ip_mask` vào
  `redact_logs` trong Caddyfile.
- Postgres không bật `log_statement` (câu SQL có thể chứa dữ liệu cá nhân).

## 7. Cập nhật phiên bản

```bash
git fetch && git checkout <tag-hoặc-nhánh> && git pull --ff-only
bash scripts/deploy-vps.sh
```
Migration luôn chạy trước khi nạp container mới và **chỉ đi tới** (không hạ). Ảnh các bản cũ được giữ lại để quay lui.

### Quay lui

Mã chỉ lùi được khi schema DB còn tương thích. Cách làm:
```bash
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E '^hoicon-(backend|web):'   # các bản đang có
HOICON_RELEASE=<mã-bản-cũ> hc up -d --wait --no-build
```
Nếu bản mới đã **migrate** và schema không còn tương thích với mã cũ: *đừng hạ migration*, hãy khôi phục dữ liệu từ bản sao
lưu trước khi migrate (mục 8) rồi chạy mã cũ. Đây là lý do bước sao lưu luôn đi trước bước migrate.

## 8. Sao lưu hằng ngày

`scripts/backup-vps.sh` sao lưu mã hóa AES-256-GCM vào `~/hoicon-backups` (hoặc `HOICON_BACKUP_DIR`) rồi xoay vòng giữ
7 bản ngày + 4 bản tuần. Chi tiết định dạng và kiểm khôi phục: `docs/setup/BACKUP.md`.

Lịch bằng systemd timer (thay `<người-dùng>` và đường dẫn repo):
```ini
# /etc/systemd/system/hoicon-backup.service
[Unit]
Description=Sao luu ma hoa Postgres HoiCon
After=docker.service
[Service]
Type=oneshot
User=<người-dùng>
WorkingDirectory=/home/<người-dùng>/hoicon
ExecStart=/usr/bin/bash scripts/backup-vps.sh

# /etc/systemd/system/hoicon-backup.timer
[Unit]
Description=Sao luu HoiCon hang ngay
[Timer]
OnCalendar=*-*-* 20:30:00 UTC
Persistent=true
[Install]
WantedBy=timers.target
```
`sudo systemctl enable --now hoicon-backup.timer`. 20:30 UTC là 03:30 giờ Việt Nam. Hằng tuần chạy
`bash scripts/backup-vps.sh restore-check` (khôi phục thử vào DB tạm rồi xóa) và đọc kết quả.

**Chưa có và cần quyết định:** bản sao lưu hiện chỉ nằm **trên chính VPS**; mất ổ hoặc mất VPS là mất cả dữ liệu lẫn sao
lưu. Cần chép ra ngoài máy (đối tượng lưu trữ hoặc máy khác, ví dụ `rclone`/`rsync` sau bước sao lưu). Tệp đã mã hóa nên
chép ra ngoài được, còn **khóa sao lưu thì không** chép cùng chỗ. Hạn lưu bản sao lưu còn ảnh hưởng quyền xóa dữ liệu của
người dùng: xem mục "Sao lưu và yêu cầu xóa" trong `docs/PRIVACY-DPIA.md`.

## 9. Vận hành thường ngày

Lệnh `ops` chạy trong container backend (đã có khóa và kết nối DB):
```bash
hc exec backend python -m hoicon.ops.pilot report --days 7 --json     # báo cáo thí điểm
hc exec backend python -m hoicon.ops.pilot gate-m2
hc exec backend python -m hoicon.ops.data request-delete --family <id> --confirm   # xóa dữ liệu một gia đình
hc exec backend python -m hoicon.ops.devices revoke --device <id>
```
Nạp tệp danh sách đe dọa thật (tệp `is_demo` bị từ chối ở prod): gắn tệp vào container dùng một lần, ví dụ
`hc run --rm --no-deps -v "$PWD/threat.json:/tmp/threat.json:ro" backend python -m hoicon.ops.threat_list load /tmp/threat.json`.
Job hạn lưu dữ liệu chạy mỗi ngày trong worker, không cần lịch ngoài.

## 10. Sự cố thường gặp

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Script dừng ở "Kiểm biến": liệt kê tên biến | Thiếu/sai định dạng/khóa trùng | Sửa `infra/.env.prod` theo gợi ý trong thông báo |
| `/readyz` 503 `missing` | Thiếu pepper, khóa dữ liệu hoặc khóa JWT | Điền khóa, chạy lại script |
| `/readyz` 503 `misconfigured: zalo_mode` | Prod mà Zalo đang mock | Compose đã ép `live`; kiểm `HOICON_ZALO_BOT_TOKEN` có giá trị |
| `/readyz` 503 `db: down` | Postgres chưa healthy hoặc sai mật khẩu | `hc ps`, `hc logs postgres`; mật khẩu trong tệp biến phải trùng mật khẩu đã khởi tạo volume |
| Caddy không cấp chứng chỉ | DNS chưa trỏ đúng, cổng 80/443 bị chặn | `hc logs caddy`; kiểm DNS và tường lửa. Let's Encrypt giới hạn số lần thử: sửa xong mới thử lại |
| Đổi `POSTGRES_PASSWORD` mà backend không vào được DB | Mật khẩu chỉ có tác dụng lúc **tạo** volume | Đặt lại mật khẩu trong DB (`ALTER ROLE`) cho khớp, hoặc trả tệp biến về giá trị cũ |
| Hết ổ đĩa | Ảnh cũ, nhật ký, bản sao lưu | `docker image prune` (giữ vài bản gần nhất để quay lui), kiểm `~/hoicon-backups` |

## 11. Đã kiểm gì và chưa kiểm gì

**Đã kiểm trên máy dev (17/10/2026), bằng chính `scripts/deploy-vps.sh` với tệp biến giả, tên miền `*.localhost`
(chứng chỉ nội bộ của Caddy), trong project compose riêng:**

- Triển khai lần đầu từ DB trống và lần hai (lũy đẳng, có sao lưu trước migrate): cả hai kết thúc bằng `/readyz` 200 qua
  Caddy, `zalo_mode: live`, web `/login` 200, `/docs` 404. Migration chạy 0001 → 0010.
- Backend chạy bằng uid 10001, rootfs chỉ đọc, bỏ hết capability; không có khóa sao lưu trong môi trường container.
- Postgres không ra được Internet, không có cổng xuất ra; backend ra được Internet (Zalo/Anthropic cần).
- Sao lưu mã hóa tạo bản `0600` rồi `restore-check` đạt (24 bảng, trigger bất biến còn nguyên, DB tạm đã xóa).
- Caddy: định tuyến đúng; `/mcp/*`, `/docs`, `/redoc`, `/openapi.json` trả 404; chống giả mạo `X-Forwarded-For`; thân
  quá 300 KB bị chặn 413 (cả chunked); SSE giữ nguyên nhịp (4 sự kiện cách nhau 0,5 s, không bị gộp); nhật ký che token.
- Script từ chối: tệp biến quyền lỏng, thiếu/sai định dạng biến, khóa trùng giá trị; thoát mã 1 kèm hướng dẫn gỡ lỗi
  khi `/readyz` không bao giờ 200, khi backend không healthy, và khi migrate hỏng (sai mật khẩu Postgres) — trường hợp
  cuối dừng *trước* khi đụng tới container đang chạy.
- Các lệnh `ops` ở mục 9 chạy được trong container (`pilot`, `data`, `devices`, `threat_list`, `zalo_webhook`; riêng
  `zalo_webhook set/info` chưa chạy vì cần token Zalo thật).

**Chưa kiểm — cần làm trên VPS thật:**

- Cấp chứng chỉ Let's Encrypt thật (máy dev chỉ thử chứng chỉ nội bộ), HTTP/3, và thời gian build/khôi phục trên cấu hình
  VPS thật. Mọi con số thời gian ở trên là của máy dev.
- Luồng SSE `: ping` thật qua Caddy với phiên người giám hộ thật (mới thử với upstream giả; backend thật chỉ được thử
  tới mức 401 không token).
- CSP mới kiểm trên Chromium với `/login` và đường chuyển hướng `/incidents` → `/login?het-han=1` (hiển thị và hydrate
  bình thường, không có vi phạm CSP). Chưa kiểm các trang sau đăng nhập (`/incidents/<id>`, `/a/<token>`).
- Webhook Zalo thật (cần token bot thật và tên miền công khai).

**Giới hạn đã biết:**

- `infra/postgres/roles.sql` (tách quyền ứng dụng khỏi chủ bảng, spec 034) **chưa được áp dụng** ở prod: ứng dụng vẫn kết
  nối bằng role chủ `hoicon` vì LangGraph chạy DDL khi khởi động (`AsyncPostgresSaver.setup()`). Hàng rào "không sửa được
  `consents`" ở prod hiện chỉ là trigger, chưa phải quyền. Cần chạy `setup()` một lần bằng role chủ trước khi chuyển.
- Hạn mức tần suất và hạn mức MCP đếm **trong bộ nhớ** (ADR-002): chỉ chạy **một** bản backend, không nhân đôi.
- Chưa có giám sát: nên đặt một dịch vụ kiểm tra bên ngoài gọi `/readyz` mỗi phút và báo về điện thoại của đội.
- Ảnh web nặng ≈ 1,4 GB vì cài cả gói phát triển; chỉ tốn đĩa, chưa tối ưu bằng build nhiều tầng.
- CSP cho phép `'unsafe-inline'` cho script và style vì Next.js nhúng script khởi tạo trong HTML (chưa dùng nonce).
- `/readyz` công khai (theo yêu cầu để giám sát bên ngoài). Nó chỉ nêu *tên* khóa thiếu, không giá trị.
- Chưa có chủ động tự động cập nhật bản vá hệ điều hành (`unattended-upgrades`) và quay vòng chứng chỉ ngoài Caddy.
