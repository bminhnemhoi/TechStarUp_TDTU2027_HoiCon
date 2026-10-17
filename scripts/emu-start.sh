#!/usr/bin/env bash
# Khởi động một AVD HỏiCon và chờ tới khi sẵn sàng. Xem docs/EMULATOR.md.
#   bash scripts/emu-start.sh hc-api36              # có cửa sổ (quay video, thao tác tay)
#   bash scripts/emu-start.sh hc-api34 --headless   # không cửa sổ (test tự động)
#   bash scripts/emu-start.sh hc-api29 --cold       # bỏ qua snapshot
#   HC_GPU=host|auto|swangle|lavapipe bash scripts/emu-start.sh hc-api36   # đổi chế độ đồ họa
#     Mặc định: Windows `auto`; Linux có cửa sổ `host` (GPU thật, mượt nhất); Linux --headless `auto` (SwiftShader,
#     ổn định, giật ~4%). Đo 15/10/2026 trên CachyOS + RTX 4060: `-gpu host` + `-no-window` SIGSEGV (gfxstream) sau ~10 lần
#     mở app liên tục; `auto`/`swangle` sống 30/30 vòng. Orca chạy AVD bằng `-no-window` ⇒ hw.gpu.mode của AVD đặt `auto`.
# Dừng: adb emu kill.  Gọi thẳng emulator vì `android emulator start|list` không đọc ANDROID_AVD_HOME.
# Chạy được trên Windows (Git Bash) và Linux — đường dẫn theo scripts/android-env.sh.
set -euo pipefail
. "$(dirname "$0")/android-env.sh"

AVD="${1:?Cần tên AVD: hc-api36 | hc-api34 | hc-api29}"
shift
LOG="${TMPDIR:-${TEMP:-/tmp}}/emu-$AVD.log"
[ "$HC_OS" = windows ] && LOG="$ANDROID_ROOT/emu-$AVD.log"

FLAGS=(-avd "$AVD" -timezone Asia/Ho_Chi_Minh -no-boot-anim -no-metrics)
HEADLESS=0
[ -n "${HC_EMU_EXTRA:-}" ] && read -r -a EXTRA <<<"$HC_EMU_EXTRA" && FLAGS+=("${EXTRA[@]}")   # cờ emulator tùy ý, vd "-feature -Vulkan"
for a in "$@"; do
  case "$a" in
    --headless) FLAGS+=(-no-window -no-audio); HEADLESS=1 ;;
    --cold) FLAGS+=(-no-snapshot-load) ;;
    *) echo "Tham số lạ: $a" >&2; exit 2 ;;
  esac
done

if "$ADB" devices | grep -q "^emulator-"; then
  echo "Đã có máy ảo đang chạy (mỗi lúc chỉ 1 AVD vì RAM):" >&2
  "$ADB" devices >&2
  exit 1
fi

if [ -z "${HC_GPU:-}" ]; then
  if [ "$HC_OS" != linux ]; then HC_GPU=auto; elif [ "$HEADLESS" = 1 ]; then HC_GPU=auto; else HC_GPU=host; fi
fi
FLAGS+=(-gpu "$HC_GPU")

"$EMU" -list-avds | grep -qx "$AVD" || { echo "Không có AVD $AVD — chạy bash scripts/avd-create.sh" >&2; exit 1; }

echo "== Khởi động $AVD (log: $LOG)"
nohup "$EMU" "${FLAGS[@]}" >"$LOG" 2>&1 &

start=$SECONDS
"$ADB" wait-for-device
until [ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
  if [ $((SECONDS - start)) -gt 300 ]; then
    echo "!! Quá 300 s chưa boot xong — xem $LOG" >&2
    exit 1
  fi
  sleep 2
done

# Trạng thái chuẩn cho kịch bản: giờ VN, tiếng Việt, cỡ chữ 1.0, không khóa màn hình khi chạy test.
"$ADB" shell cmd alarm set-timezone Asia/Ho_Chi_Minh >/dev/null 2>&1 || true
if [ "$("$ADB" shell settings get system system_locales | tr -d '\r')" != "vi-VN" ]; then
  "$ADB" shell settings put system system_locales vi-VN
  echo "   Đã đặt system_locales=vi-VN — có hiệu lực sau lần khởi động lại kế tiếp."
fi
"$ADB" shell settings put system font_scale 1.0
"$ADB" shell svc power stayon true
"$ADB" shell input keyevent KEYCODE_WAKEUP

sdk=$("$ADB" shell getprop ro.build.version.sdk | tr -d '\r')
locale=$("$ADB" shell getprop persist.sys.locale | tr -d '\r')
# Lệnh shell trên máy ảo phải là MỘT chuỗi, nếu không định dạng có dấu cách bị tách ("date: Max 1 argument").
echo "== $AVD sẵn sàng sau $((SECONDS - start)) s · API $sdk · locale ${locale:-mặc định} · $("$ADB" shell "date '+%H:%M %Z'" | tr -d '\r')"
