#!/usr/bin/env bash
# Cổng phát hành HỏiCon (spec 029 FR-005, MASTER-PLAN checklist release-block): đọc CHÍNH tệp phát hành (APK/AAB),
# không đọc mã nguồn, nên bắt được cả lỗi cấu hình Gradle (thư viện kéo thêm quyền vào manifest đã gộp, R8 tắt...).
#
#   scripts/release-gate.sh <app.apk|app.aab>
#
# Mỗi mục ra [ĐẠT] / [TRƯỢT]; mục không tự động được in [KIỂM TAY]. Thoát 0 chỉ khi không mục nào TRƯỢT.
#   exit 0 = đạt · 1 = có mục TRƯỢT (hoặc BỎ QUA) · 2 = dùng sai / thiếu công cụ hoặc tệp (UNAVAILABLE, không phải "đạt")
# HC_GATE_SKIP_PIN_TEST=1 bỏ qua bước chạy ConsentTextsPinTest (Gradle, chậm); mục đó in [BỎ QUA] và tính là TRƯỢT,
# nên cờ này không thể làm cổng "xanh" giả.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export LC_ALL=C.UTF-8

if [ "$#" -ne 1 ]; then
  echo "Dùng: scripts/release-gate.sh <app.apk|app.aab>" >&2
  exit 2
fi
FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "Không thấy tệp phát hành: $FILE" >&2
  exit 2
fi
case "$FILE" in
  *.apk) KIND=apk ;;
  *.aab) KIND=aab ;;
  *) echo "Chỉ nhận .apk hoặc .aab: $FILE" >&2; exit 2 ;;
esac

# --- Công cụ: SDK + JDK theo scripts/android-env.sh (apkanalyzer cần java) --------------------------------------
# shellcheck source=scripts/android-env.sh
. "$ROOT/scripts/android-env.sh"
if [ -z "${JAVA_HOME:-}" ]; then
  for jdk in "$JDK_DIR" /opt/android-studio/jbr; do
    if [ -x "$jdk/bin/java" ]; then export JAVA_HOME="$jdk"; break; fi
  done
fi
[ -n "${JAVA_HOME:-}" ] && export PATH="$JAVA_HOME/bin:$PATH"
AAPT2="$(ls -d "$SDK"/build-tools/*/aapt2"$EXE" 2>/dev/null | sort -V | tail -n 1)"
APKANALYZER="$SDK/cmdline-tools/latest/bin/apkanalyzer$BAT"
for tool in "$AAPT2" "$APKANALYZER"; do
  if [ -z "$tool" ] || [ ! -x "$tool" ]; then
    echo "UNAVAILABLE: thiếu công cụ Android SDK (aapt2/apkanalyzer) dưới $SDK" >&2
    exit 2
  fi
done
command -v java >/dev/null || { echo "UNAVAILABLE: thiếu java (JAVA_HOME)" >&2; exit 2; }
for tool in unzip zip awk; do
  command -v "$tool" >/dev/null || { echo "UNAVAILABLE: thiếu lệnh $tool" >&2; exit 2; }
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Chuẩn hóa: AAB -> "APK nhị phân" để mọi mục dùng cùng một công cụ ---------------------------------------------
# AAB lưu manifest/tài nguyên dạng protobuf (base/manifest, base/resources.pb); aapt2 convert đổi về dạng nhị phân.
VIEW="$FILE"
PROGUARD_MAP=""
if [ "$KIND" = aab ]; then
  mkdir -p "$TMP/aab" "$TMP/stage"
  unzip -q "$FILE" 'base/*' -d "$TMP/aab" || { echo "Không giải nén được AAB: $FILE" >&2; exit 2; }
  unzip -Z1 "$FILE" >"$TMP/aab-entries.txt"
  if grep -q '^BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map$' "$TMP/aab-entries.txt"; then
    PROGUARD_MAP=present
  fi
  cp "$TMP/aab/base/manifest/AndroidManifest.xml" "$TMP/stage/AndroidManifest.xml"
  cp "$TMP/aab/base/resources.pb" "$TMP/stage/resources.pb"
  [ -d "$TMP/aab/base/res" ] && cp -r "$TMP/aab/base/res" "$TMP/stage/res"
  [ -d "$TMP/aab/base/dex" ] && cp "$TMP/aab/base/dex/"*.dex "$TMP/stage/"
  (cd "$TMP/stage" && zip -qr "$TMP/proto.apk" .)
  "$AAPT2" convert --output-format binary -o "$TMP/view.apk" "$TMP/proto.apk" 2>"$TMP/convert.log" \
    || { echo "aapt2 convert thất bại:"; cat "$TMP/convert.log"; exit 2; }
  VIEW="$TMP/view.apk"
fi

MANIFEST="$TMP/manifest.txt"
"$AAPT2" dump xmltree --file AndroidManifest.xml "$VIEW" >"$MANIFEST" 2>&1 \
  || { echo "Không đọc được manifest đã gộp của $FILE"; cat "$MANIFEST"; exit 2; }

# --- In kết quả ----------------------------------------------------------------------------------------------------
FAILS=0
pass() { echo "[ĐẠT]      $1"; }
fail() { echo "[TRƯỢT]    $1"; FAILS=$((FAILS + 1)); }
skip() { echo "[BỎ QUA]   $1 (tính là TRƯỢT)"; FAILS=$((FAILS + 1)); }
manual() { echo "[KIỂM TAY] $1"; }
note() { printf '             %s\n' "$1"; }

echo "Cổng phát hành HỏiCon — $FILE"
echo "  loại: $KIND · kích thước: $(wc -c <"$FILE") byte · sha256: $(sha256sum "$FILE" | cut -d' ' -f1)"
echo

# 1. Quyền / dịch vụ bị cấm (CLAUDE.md luật 3, ADR-007). Danh sách = danh sách của hook guard-privacy + CAMERA,
#    WRITE_CONTACTS, RECEIVE_WAP_PUSH; scripts/tests/test_release_gate.py kiểm danh sách này luôn chứa danh sách của hook.
FORBIDDEN_PERMISSIONS=(
  android.permission.READ_SMS
  android.permission.RECEIVE_SMS
  android.permission.SEND_SMS
  android.permission.RECEIVE_MMS
  android.permission.RECEIVE_WAP_PUSH
  android.permission.READ_CALL_LOG
  android.permission.WRITE_CALL_LOG
  android.permission.PROCESS_OUTGOING_CALLS
  android.permission.READ_CONTACTS
  android.permission.WRITE_CONTACTS
  android.permission.CAMERA
  android.permission.QUERY_ALL_PACKAGES
  android.permission.REQUEST_INSTALL_PACKAGES
  android.permission.RECORD_AUDIO_CALL
  android.permission.CAPTURE_AUDIO_OUTPUT
  android.permission.BIND_ACCESSIBILITY_SERVICE
  android.permission.BIND_NOTIFICATION_LISTENER_SERVICE
)
# Dịch vụ Accessibility / Notification Listener chỉ cần khai báo intent-filter là đã là dịch vụ cấm.
FORBIDDEN_ACTIONS=(
  android.accessibilityservice.AccessibilityService
  android.service.notification.NotificationListenerService
)
HITS=()
for name in "${FORBIDDEN_PERMISSIONS[@]}" "${FORBIDDEN_ACTIONS[@]}"; do
  if grep -aqF "\"$name\"" "$MANIFEST"; then HITS+=("$name"); fi
done
if [ "${#HITS[@]}" -eq 0 ]; then
  pass "Quyền cấm: manifest đã gộp không có quyền/dịch vụ nào trong danh sách cấm (${#FORBIDDEN_PERMISSIONS[@]} quyền, ${#FORBIDDEN_ACTIONS[@]} dịch vụ)"
else
  fail "Quyền cấm: manifest đã gộp khai báo ${HITS[*]}"
  note "Tìm thư viện kéo quyền vào: ./gradlew :app:processReleaseManifest rồi xem build/intermediates/merged_manifests/release/ (manifest-merger-release-report.txt)"
fi

# 2. Không được debuggable.
if grep -aq 'debuggable.*=true' "$MANIFEST"; then
  fail "Debuggable: android:debuggable=true (bản phát hành không được cho gỡ lỗi)"
else
  pass "Debuggable: tắt"
fi

# 3. R8 bật. AAB: có proguard.map trong BUNDLE-METADATA. APK không mang mapping, nên đo tên lớp: R8 đổi hầu hết tên lớp thành 1-2 chữ.
DEX_VIEW="$TMP/dexview.apk"
if [ "$KIND" = aab ]; then
  cp "$VIEW" "$DEX_VIEW"
else
  DEX_VIEW="$FILE"
fi
"$APKANALYZER" dex packages --defined-only "$DEX_VIEW" >"$TMP/classes.tsv" 2>"$TMP/apkanalyzer.log" \
  || { echo "apkanalyzer thất bại:"; cat "$TMP/apkanalyzer.log"; exit 2; }
# Ngưỡng 10% đặt giữa hai số đo thật (spec 029): bản debug 3/23533 lớp (0,01%), bản release bật R8 959/3900 lớp (24%) — R8 vẫn
# giữ tên các lớp Room/Compose/điểm vào manifest nên không bao giờ đạt 100%.
R8_MIN_PCT=10
# Tên lớp "rút gọn" = 1-2 ký tự (a, b, ab, a$b); lớp R của tài nguyên không tính (R8 vốn đã nội tuyến chúng).
read -r TOTAL SHORT < <(awk -F'\t' '
  /^C / {
    n = split($NF, p, "."); simple = p[n]; total++
    if (simple ~ /^[A-Za-z][A-Za-z0-9]?(\$[A-Za-z][A-Za-z0-9]?)*$/ && simple !~ /^R(\$|$)/) short++
  }
  END { printf "%d %d\n", total, short }' "$TMP/classes.tsv")
RATIO_PCT=0
[ "$TOTAL" -gt 0 ] && RATIO_PCT=$((SHORT * 100 / TOTAL))
R8_OK=0
if [ "$KIND" = aab ]; then
  [ -n "$PROGUARD_MAP" ] && [ "$RATIO_PCT" -ge "$R8_MIN_PCT" ] && R8_OK=1
else
  [ "$RATIO_PCT" -ge "$R8_MIN_PCT" ] && R8_OK=1
fi
if [ "$R8_OK" -eq 1 ]; then
  pass "R8: $SHORT/$TOTAL lớp ($RATIO_PCT%) có tên rút gọn${PROGUARD_MAP:+, có proguard.map trong AAB}"
else
  fail "R8: chưa bật/chưa rút gọn — $SHORT/$TOTAL lớp ($RATIO_PCT%) có tên rút gọn, cần ≥ $R8_MIN_PCT%"
  if [ "$KIND" = aab ] && [ -z "$PROGUARD_MAP" ]; then
    note "AAB không có BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map"
  fi
  note "Lớp mẫu còn nguyên tên: $(awk -F'\t' '/^C / && $NF ~ /^vn\.hoicon\./ { print $NF; exit }' "$TMP/classes.tsv")"
  note "Kiểm tra buildType release có isMinifyEnabled = true và tệp proguard (spec 012); bản debug luôn TRƯỢT mục này"
fi

# 4. Không còn nhật ký chẩn đoán spike trong dex.
DEX_HITS=()
for dex in $(unzip -Z1 "$DEX_VIEW" | grep -E '^classes[0-9]*\.dex$'); do
  count="$(unzip -p "$DEX_VIEW" "$dex" | grep -a -c -E 'HC_TIMING|HC_SPIKE' || true)"
  if [ "${count:-0}" -gt 0 ]; then DEX_HITS+=("$dex"); fi
done
if [ "${#DEX_HITS[@]}" -eq 0 ]; then
  pass "Nhật ký spike: dex không chứa HC_TIMING/HC_SPIKE"
else
  fail "Nhật ký spike: HC_TIMING/HC_SPIKE còn trong ${DEX_HITS[*]}"
  note "Cổng BuildConfig.DEBUG phải bị R8 loại bỏ ở bản phát hành"
fi

# 5. Không cho phép cleartext (http://): cờ usesCleartextTraffic hoặc network-security-config cho phép.
CLEARTEXT_WHY=()
if grep -aq 'usesCleartextTraffic.*=true' "$MANIFEST"; then CLEARTEXT_WHY+=("android:usesCleartextTraffic=true"); fi
NSC_ID="$(grep -a 'networkSecurityConfig' "$MANIFEST" | grep -a -o '@0x[0-9a-f]*' | head -n 1 | sed 's/^@//')"
if [ -n "$NSC_ID" ]; then
  "$AAPT2" dump resources "$VIEW" >"$TMP/resources.txt" 2>&1 || true
  NSC_FILE="$(awk -v id="$NSC_ID" '
    $1 == "resource" && $2 == id { found = 1; next }
    found && /\(file\)/ { for (i = 1; i <= NF; i++) if ($i ~ /^res\//) { print $i; exit } }
    found && $1 == "resource" { exit }' "$TMP/resources.txt")"
  if [ -n "$NSC_FILE" ] && "$AAPT2" dump xmltree --file "$NSC_FILE" "$VIEW" >"$TMP/nsc.txt" 2>&1; then
    if grep -aq 'cleartextTrafficPermitted=true' "$TMP/nsc.txt"; then CLEARTEXT_WHY+=("$NSC_FILE cho phép cleartext"); fi
  else
    CLEARTEXT_WHY+=("không đọc được network-security-config ($NSC_ID)")
  fi
fi
if [ "${#CLEARTEXT_WHY[@]}" -eq 0 ]; then
  pass "Cleartext: bị chặn (không có cờ usesCleartextTraffic, không có network-security-config cho phép http://)"
else
  fail "Cleartext: ${CLEARTEXT_WHY[*]}"
fi

# 6. Công khai AI (CLAUDE.md luật 6).
# (ghi ra tệp rồi mới grep: grep -q thoát sớm làm đường ống dính SIGPIPE và pipefail báo sai)
"$AAPT2" dump strings "$VIEW" >"$TMP/strings.txt" 2>/dev/null
if grep -aqF 'Đây là trợ lý AI HỏiCon' "$TMP/strings.txt"; then
  pass "Công khai AI: có chuỗi \"Đây là trợ lý AI HỏiCon\" trong tài nguyên"
else
  fail "Công khai AI: không thấy \"Đây là trợ lý AI HỏiCon\" trong tài nguyên chuỗi"
fi

# 7. Văn bản đồng ý đã ghim hash (đổi chữ ⇒ phải đổi phiên bản đồng ý).
if [ "${HC_GATE_SKIP_PIN_TEST:-}" = 1 ]; then
  skip "ConsentTextsPinTest: bị bỏ qua bằng HC_GATE_SKIP_PIN_TEST=1"
else
  if "$ROOT/apps/android/gradlew" -p "$ROOT/apps/android" :app:testDebugUnitTest --tests '*ConsentTextsPinTest' \
      --console=plain -q >"$TMP/pin.log" 2>&1; then
    pass "ConsentTextsPinTest: hash văn bản đồng ý khớp"
  else
    fail "ConsentTextsPinTest: không đạt"
    tail -n 15 "$TMP/pin.log" | while IFS= read -r line; do note "$line"; done
  fi
fi

# 8. Mục không tự động được.
manual "Người dùng thí điểm đều ≥ 18 tuổi (ghi danh bằng \`ops pilot enroll --confirm-adult\`)"
manual "privacy-audit sạch (số điện thoại/tài khoản/OTP thô, che PII, đồng ý theo mục đích)"

echo
if [ "$FAILS" -eq 0 ]; then
  echo "KẾT QUẢ: ĐẠT mọi mục tự động. Còn các mục [KIỂM TAY] cho người."
  exit 0
fi
echo "KẾT QUẢ: TRƯỢT $FAILS mục — không phát hành."
exit 1
