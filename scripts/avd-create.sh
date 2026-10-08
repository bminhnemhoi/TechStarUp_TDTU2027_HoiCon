#!/usr/bin/env bash
# Tạo ma trận máy ảo HỏiCon trên D: (idempotent). Xem docs/EMULATOR.md.
#   bash scripts/avd-create.sh            # tạo hc-api36, hc-api34, hc-api29 nếu chưa có
#   bash scripts/avd-create.sh --recreate # xóa và tạo lại (mất dữ liệu trong máy ảo)
# Gọi thẳng lớp Java của avdmanager: avdmanager.bat chạy qua cmd.exe sẽ tách tham số tại dấu ';'
# trong "system-images;android-36;…" (cùng lỗi với sdkmanager.bat).
set -euo pipefail

SDK="${ANDROID_HOME:-D:/Android/Sdk}"
JAVA="${HOICON_JDK:-D:/Android/jdk-21}/bin/java.exe"
export ANDROID_HOME="$SDK" ANDROID_SDK_ROOT="$SDK" ANDROID_AVD_HOME="${ANDROID_AVD_HOME:-D:/Android/avd}"
TOOLS="$SDK/cmdline-tools/latest"
RECREATE="${1:-}"

avdm() {
  "$JAVA" -Dcom.android.sdkmanager.toolsdir="$TOOLS" -classpath "$TOOLS/lib/avdmanager-classpath.jar" \
    com.android.sdklib.tool.AvdManagerCli "$@"
}

# name | api | device profile | RAM MB | data partition
MATRIX=(
  "hc-api36|36|pixel_6|2048|6G"     # máy chính: targetSdk, giới hạn khởi chạy nền mới nhất
  "hc-api34|34|pixel_4a|2048|4G"    # Android 14: giới hạn full-screen intent
  "hc-api29|29|small_phone|1536|4G" # minSdk, màn hình nhỏ ~ máy cũ của người cao tuổi
)

set_prop() { # file key value — thay hoặc thêm dòng key=value
  if grep -q "^$2=" "$1"; then sed -i "s|^$2=.*|$2=$3|" "$1"; else echo "$2=$3" >>"$1"; fi
}

mkdir -p "$ANDROID_AVD_HOME"
for row in "${MATRIX[@]}"; do
  IFS='|' read -r name api device ram data <<<"$row"
  pkg="system-images;android-$api;google_apis_playstore;x86_64"
  if [ ! -d "$SDK/system-images/android-$api/google_apis_playstore/x86_64" ]; then
    echo "!! Thiếu $pkg — chạy scripts/setup-android.sh trước" >&2
    continue
  fi
  if [ -d "$ANDROID_AVD_HOME/$name.avd" ]; then
    if [ "$RECREATE" = "--recreate" ]; then
      avdm delete avd -n "$name"
    else
      echo "== $name đã có — bỏ qua (dùng --recreate để tạo lại)"
      continue
    fi
  fi
  echo "== Tạo $name (API $api, $device, RAM ${ram}MB)"
  echo no | avdm create avd -n "$name" -k "$pkg" -d "$device" -p "$ANDROID_AVD_HOME/$name.avd" >/dev/null
  cfg="$ANDROID_AVD_HOME/$name.avd/config.ini"
  # Một số profile mới ghi disk.dataPartition.path=<temp> ⇒ userdata nằm trong %TEMP% (ổ C:) và mất khi tắt.
  # Bỏ dòng này để userdata-qemu.img nằm trong thư mục AVD trên D: và giữ trạng thái giữa các lần chạy.
  sed -i '/^disk\.dataPartition\.path=/d' "$cfg"
  set_prop "$cfg" hw.ramSize "$ram"
  set_prop "$cfg" vm.heapSize 256
  set_prop "$cfg" disk.dataPartition.size "$data"
  set_prop "$cfg" hw.gpu.enabled yes
  set_prop "$cfg" hw.gpu.mode auto
  set_prop "$cfg" hw.keyboard yes
  set_prop "$cfg" hw.audioInput yes
  set_prop "$cfg" fastboot.forceColdBoot no
  set_prop "$cfg" showDeviceFrame yes
done

echo
avdm list avd -c
