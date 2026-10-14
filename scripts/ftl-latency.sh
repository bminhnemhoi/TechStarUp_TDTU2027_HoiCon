#!/usr/bin/env bash
# Đo độ trễ "mở app ngân hàng → SafePause hiện" trên MÁY THẬT của Firebase Test Lab (P1-S2, đóng ADR-007).
# Bộ đo: apps/android/latency (SafePauseLatencyTest) — cuộc gọi được mô phỏng bằng receiver chỉ có ở bản debug
# (máy FTL không có SIM), phần còn lại là đường găng thật. App ngân hàng thật KHÔNG chạy được trên FTL (ADB bật ⇒
# Thông tư 77/2025/TT-NHNN buộc app ngân hàng dừng) nên đo với :demobank.
#
# Cần: gcloud đã đăng nhập + dự án Firebase (P0-08). Gói Spark: 5 lượt máy thật/ngày.
#   gcloud firebase test android models list --filter="form=PHYSICAL"      # chọn model/version
#   bash scripts/ftl-latency.sh model=a15,version=34 model=oriole,version=33
# Kết quả: logcat tag HC_LATENCY + latency.json trong thư mục kết quả trên Cloud Storage (in ra cuối lệnh).
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Dùng: $0 model=<id>,version=<api> [model=...,version=...]" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/apps/android" && ./gradlew -q :app:assembleDebug :demobank:assembleDebug :latency:assembleDebug)

OUT="$ROOT/apps/android"
devices=()
for d in "$@"; do devices+=(--device "$d,locale=vi,orientation=portrait"); done

gcloud firebase test android run \
  --type instrumentation \
  --app "$OUT/app/build/outputs/apk/debug/app-debug.apk" \
  --test "$OUT/latency/build/outputs/apk/debug/latency-debug.apk" \
  --additional-apks "$OUT/demobank/build/outputs/apk/debug/demobank-debug.apk" \
  --environment-variables runs=10,compile=speed \
  --directories-to-pull /sdcard/Android/data/vn.hoicon.latency/files \
  --timeout 30m \
  "${devices[@]}"
