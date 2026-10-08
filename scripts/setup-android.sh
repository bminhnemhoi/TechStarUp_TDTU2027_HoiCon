#!/usr/bin/env bash
# Cài bộ công cụ Android cho HỏiCon KHÔNG cần quyền admin, mọi thứ nằm trên ổ D:
#   - JDK 21 (Temurin, bản zip) để chạy Gradle/sdkmanager — không đụng JAVA_HOME toàn hệ thống (JDK 25)
#   - Android SDK command-line tools, platform-tools, emulator, platform 36, build-tools 36.1.0
#   - Ảnh hệ thống Google Play x86_64 cho API 36 (máy chính), 34, 29 (minSdk)
# Chạy lại an toàn (bỏ qua bước đã xong). Dùng Git Bash:  bash scripts/setup-android.sh
set -euo pipefail

ANDROID_ROOT="${ANDROID_ROOT:-D:/Android}"
SDK="$ANDROID_ROOT/Sdk"
JDK_DIR="$ANDROID_ROOT/jdk-21"
TMP="$ANDROID_ROOT/.downloads"
mkdir -p "$SDK" "$TMP"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

# 1) JDK 21 ---------------------------------------------------------------
if [ ! -x "$JDK_DIR/bin/java.exe" ]; then
  log "Tải Temurin JDK 21 (zip)..."
  curl -fSL -o "$TMP/jdk21.zip" \
    "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk"
  rm -rf "$TMP/jdk21" && mkdir -p "$TMP/jdk21"
  unzip -q "$TMP/jdk21.zip" -d "$TMP/jdk21"
  rm -rf "$JDK_DIR" && mv "$TMP"/jdk21/jdk-21* "$JDK_DIR"
fi
log "JDK: $("$JDK_DIR/bin/java.exe" -version 2>&1 | head -1)"
export JAVA_HOME="$JDK_DIR"

# 2) Command-line tools (lấy bản mới nhất từ repository2-3.xml) ------------
SDKM="$SDK/cmdline-tools/latest/bin/sdkmanager.bat"
if [ ! -f "$SDKM" ]; then
  log "Dò bản cmdline-tools mới nhất..."
  curl -fsSL -o "$TMP/repo2.xml" https://dl.google.com/android/repository/repository2-3.xml
  ZIP=$(python -c "import re;x=open(r'$TMP/repo2.xml',encoding='utf-8').read();b=re.search(r'<remotePackage path=\"cmdline-tools;latest\">(.*?)</remotePackage>',x,re.S).group(1);print(re.search(r'<url>(commandlinetools-win[^<]+)</url>',b).group(1))")
  log "Tải $ZIP"
  curl -fSL -o "$TMP/cmdline.zip" "https://dl.google.com/android/repository/$ZIP"
  rm -rf "$TMP/cmdline" && mkdir -p "$TMP/cmdline" "$SDK/cmdline-tools"
  unzip -q "$TMP/cmdline.zip" -d "$TMP/cmdline"
  rm -rf "$SDK/cmdline-tools/latest" && mv "$TMP/cmdline/cmdline-tools" "$SDK/cmdline-tools/latest"
fi

# 3) Gói SDK -------------------------------------------------------------
PKGS=(
  "platform-tools"
  "emulator"
  "platforms;android-36"
  "build-tools;36.1.0"
  "system-images;android-36;google_apis_playstore;x86_64"
  "system-images;android-34;google_apis_playstore;x86_64"
  "system-images;android-29;google_apis_playstore;x86_64"
)
log "Chấp nhận giấy phép SDK..."
yes | "$SDKM" --sdk_root="$SDK" --licenses >/dev/null 2>&1 || true
# Từ 2026, sdkmanager.bat chỉ chuyển tiếp sang Android CLI (android.exe) và cmd.exe cắt tham số tại dấu ';'
# → gọi thẳng android.exe để tên gói có ';' được giữ nguyên.
ANDROID_CLI="$SDK/cmdline-tools/latest/bin/android.exe"
export NO_COLOR=1
for p in "${PKGS[@]}"; do
  pkg_dir="$SDK/${p//;//}"
  if [ -d "$pkg_dir" ] && [ -n "$(ls -A "$pkg_dir" 2>/dev/null)" ]; then log "Đã có $p"; continue; fi
  log "Cài $p"
  "$ANDROID_CLI" --sdk="$SDK" sdk install "$p" 2>&1 | sed -r 's/\x1B\[[0-9;]*[A-Za-z]//g' | tail -2 \
    || { log "!! Lỗi khi cài $p"; exit 1; }
  [ -d "$pkg_dir" ] || { log "!! Không thấy $pkg_dir sau khi cài $p"; exit 1; }
done

# 4) Kiểm tra ------------------------------------------------------------
log "adb: $("$SDK/platform-tools/adb.exe" version | head -1)"
log "Kiểm tra tăng tốc phần cứng của emulator:"
"$SDK/emulator/emulator.exe" -accel-check || true
log "XONG. Đặt biến môi trường (một lần) bằng: powershell -File scripts/env-android.ps1"
