#!/usr/bin/env bash
# Chạy bộ đo giọng nói tiếng Việt `:voicelab` (spike P1-S5, spec 004-voice-vi) trên MÁY ẢO / MÁY THỬ và gom bằng chứng.
#   bash scripts/voice-lab.sh --avd hc-api36 --probe tts|clip|synth|stt [--set synthetic|team] [--runs N]
#                             [--allow-network [--confirm-team-audio-to-cloud]] [--revoke-record-audio]
# Cần một máy ảo đang chạy (bash scripts/emu-start.sh hc-api36 --headless; mỗi lúc MỘT máy ảo vì RAM).
#   tts    TtsProbeTest + TtsLatencyTest   bảng giọng vi + độ trễ speak→onStart nguội/ấm   (mạng TẮT)
#   clip   ClipLatencyTest                 độ trễ phát âm thanh thu sẵn nguội/ấm          (mạng TẮT)
#   synth  SynthesizeTest                  tổng hợp WAV, kéo về $EV/wav, đổi 16 kHz mono → $EV/wav16
#   stt    SttProbeTest                    thăm dò nhận dạng vi-VN; thêm --set ⇒ SttRunTest trên bộ tệp WAV
# Bằng chứng thô ngoài repo: $HC_VOICE_EV (mặc định ~/hoicon-evidence/004-voice-vi), quyền 700.
# AN TOÀN (review bảo mật 15/10/2026):
#  - chỉ chạy trên máy ảo (hoặc máy thử có HC_VOICE_TEST_DEVICE=1); bản thu thật (--set team) trên máy thử cần thêm
#    HC_VOICE_ALLOW_TEAM_ON_DEVICE=1 sau khi chạy --set synthetic và thấy kết quả hợp lý (bộ nhận dạng tôn trọng nguồn tệp);
#  - RECORD_AUDIO mặc định THU HỒI; chỉ cấp khi cần bộ nhận dạng mặc định (--allow-network). Bộ trên máy chạy không cần quyền,
#    nên nếu nó bỏ qua nguồn tệp thì lỗi 9 thay vì mở micro;
#  - probe stt đòi chính máy ảo đó chạy `-no-audio` (emu-start.sh --headless);
#  - bản thu của đội KHÔNG bao giờ qua bộ nhận dạng mạng, trừ khi có --confirm-team-audio-to-cloud (người thu phải biết
#    âm thanh có thể gửi tới Google);
#  - thoát (kể cả lỗi) ⇒ xóa bản sao trên máy chủ/máy ảo, trả lại trạng thái mạng ban đầu.
set -euo pipefail
umask 077
. "$(dirname "$0")/android-env.sh"

PKG=vn.hoicon.voicelab
TESTDEV=false; [ "${HC_VOICE_TEST_DEVICE:-0}" = 1 ] && TESTDEV=true
RUNNER="$PKG.test/androidx.test.runner.AndroidJUnitRunner"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EV="${HC_VOICE_EV:-$HOME/hoicon-evidence/004-voice-vi}"
DEVICE_TMP=/data/local/tmp/hcvoice

AVD="" PROBE="" SET="" RUNS="" ALLOW_NET=0 REVOKE_MIC=0 CONFIRM_CLOUD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --avd) AVD="${2:?}"; shift 2 ;;
    --probe) PROBE="${2:?}"; shift 2 ;;
    --set) SET="${2:?}"; shift 2 ;;
    --runs) RUNS="${2:?}"; shift 2 ;;
    --allow-network) ALLOW_NET=1; shift ;;
    --confirm-team-audio-to-cloud) CONFIRM_CLOUD=1; shift ;;
    --revoke-record-audio) REVOKE_MIC=1; shift ;;
    *) echo "Tham số lạ: $1" >&2; exit 2 ;;
  esac
done
[ -n "$AVD" ] && [ -n "$PROBE" ] || { sed -n 2,24p "$0" >&2; exit 2; }
case "$AVD" in *[!A-Za-z0-9_-]*) echo "--avd chỉ gồm chữ, số, '_' và '-' (đi vào tên tệp bằng chứng)" >&2; exit 2 ;; esac
case "$PROBE" in tts | clip | synth | stt) ;; *) echo "--probe phải là tts|clip|synth|stt" >&2; exit 2 ;; esac
case "$SET" in "" | synthetic | team) ;; *) echo "--set phải là synthetic|team" >&2; exit 2 ;; esac
case "${RUNS:-0}" in *[!0-9]*) echo "--runs phải là số" >&2; exit 2 ;; esac
if [ "$SET" = team ] && [ "$ALLOW_NET" = 1 ] && [ "$CONFIRM_CLOUD" = 0 ]; then
  echo "!! --set team --allow-network gửi giọng người thật tới bộ nhận dạng mạng của Google. Chỉ khi người thu đã biết điều đó:" >&2
  echo "   thêm --confirm-team-audio-to-cloud (và ghi vào evidence.md). Mặc định: từ chối." >&2
  exit 2
fi

mkdir -p "$EV"/{logs,audio/team,wav,wav16,ratings}
chmod 700 "$EV" "$EV/audio" "$EV/audio/team"
STAMP="$(date +%Y%m%d-%H%M%S)"

# --- Dọn dẹp mọi đường thoát ----------------------------------------------------------------------------------------------
STAGE="" DEVICE_READY=0 WIFI0=0 DATA0=0   # chỉ đổi khi script TẮT mạng (mục 2)
cleanup() {
  [ -n "$STAGE" ] && [ -d "$STAGE" ] && rm -r "$STAGE"
  if [ "$DEVICE_READY" = 1 ]; then
    "$ADB" shell "rm -rf $DEVICE_TMP" >/dev/null 2>&1 || true
    # Bản sao WAV/kết quả nhận dạng trong app (có thể là giọng người thật): không để lại trên máy ảo/snapshot.
    "$ADB" shell "run-as $PKG sh -c 'rm -rf files/stt files/results'" >/dev/null 2>&1 || true
    "$ADB" shell pm revoke "$PKG" android.permission.RECORD_AUDIO >/dev/null 2>&1 || true   # không để quyền micro lại sau --allow-network
    [ "$WIFI0" = 1 ] && "$ADB" shell svc wifi enable >/dev/null 2>&1 || true
    [ "$DATA0" = 1 ] && "$ADB" shell svc data enable >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# --- 1. Máy đích -------------------------------------------------------------------------------------------------------
n_devices=$("$ADB" devices | grep -c -w device || true)
[ "$n_devices" = 1 ] || { echo "Cần đúng 1 thiết bị adb (đang có $n_devices)." >&2; exit 1; }
hardware=$("$ADB" shell getprop ro.hardware | tr -d '\r')
case "$hardware" in
  ranchu | goldfish) IS_EMU=1 ;;
  *)
    IS_EMU=0
    [ "${HC_VOICE_TEST_DEVICE:-0}" = 1 ] || { echo "!! $hardware không phải máy ảo. Chỉ chạy trên AVD/máy thử (HC_VOICE_TEST_DEVICE=1)." >&2; exit 1; }
    if [ "$SET" = team ] && [ "${HC_VOICE_ALLOW_TEAM_ON_DEVICE:-0}" != 1 ]; then
      echo "!! --set team trên máy thật: bộ nhận dạng của hãng có thể mở micro. Chạy --set synthetic trước, kiểm kết quả, rồi" >&2
      echo "   đặt HC_VOICE_ALLOW_TEAM_ON_DEVICE=1." >&2
      exit 2
    fi
    ;;
esac
if [ "$IS_EMU" = 1 ]; then
  actual=$("$ADB" emu avd name 2>/dev/null | head -1 | tr -d '\r')
  [ "$actual" = "$AVD" ] || { echo "!! Máy ảo đang chạy là '$actual', không phải '$AVD'." >&2; exit 1; }
  # `-no-audio` phải nằm trên đúng tiến trình của AVD này (không phải bất kỳ tiến trình nào có chữ emulator).
  if [ "$PROBE" = stt ] && ! pgrep -af -- "-avd $AVD" | grep -E -- "[[:space:]]-avd[[:space:]]+$AVD([[:space:]]|\$)" | grep -q -- '-no-audio'; then
    echo "!! probe stt chỉ chạy khi máy ảo $AVD có -no-audio (không mở micro máy chủ): bash scripts/emu-start.sh $AVD --headless" >&2
    exit 1
  fi
fi
DEVICE_READY=1
free_gb=$(free -m 2>/dev/null | awk '/^Mem:/ {printf "%.1f", $7/1024}' || true); free_gb="${free_gb:-?}"   # `free` chỉ có trên Linux
echo "== $AVD ($hardware) · probe=$PROBE set=${SET:--} · RAM khả dụng ${free_gb} GB · bằng chứng: $EV"

# --- 2. Mạng ------------------------------------------------------------------------------------------------------------
NETOFF=false
if [ "$ALLOW_NET" = 0 ]; then
  NETOFF=true
  WIFI0=$("$ADB" shell settings get global wifi_on | tr -d '\r')
  DATA0=$("$ADB" shell settings get global mobile_data | tr -d '\r')
  "$ADB" shell svc wifi disable
  "$ADB" shell svc data disable
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    "$ADB" shell "ping -c 1 -W 2 8.8.8.8" >/dev/null 2>&1 || break
    sleep 1
  done
  if "$ADB" shell "ping -c 1 -W 2 8.8.8.8" >/dev/null 2>&1; then
    echo "!! Mạng vẫn thông sau khi tắt Wi-Fi/dữ liệu — không đo ở trạng thái offline." >&2
    exit 1
  fi
  net_state=$("$ADB" shell dumpsys connectivity 2>/dev/null | grep -i -m1 "Active default network" | tr -d '\r' || true)
  echo "   mạng TẮT (ping 8.8.8.8 thất bại; dumpsys connectivity: ${net_state:-không có dòng 'Active default network'})"
  echo "   sẽ trả lại trạng thái ban đầu (wifi=$WIFI0 data=$DATA0) khi xong"
else
  echo "   !! --allow-network: bộ nhận dạng mặc định có thể dùng mạng — nhãn 'mạng, không dùng cho sản phẩm'"
fi

# --- 3. Cài bộ đo -------------------------------------------------------------------------------------------------------
(cd "$ROOT" && JAVA_HOME="${JAVA_HOME:-$JDK_DIR}" apps/android/gradlew -p apps/android -q \
  :voicelab:assembleDebug :voicelab:assembleDebugAndroidTest)
APK_DIR="$ROOT/apps/android/voicelab/build/outputs/apk"
"$ADB" install -r -t "$APK_DIR/debug/voicelab-debug.apk" >/dev/null
"$ADB" install -r -t "$APK_DIR/androidTest/debug/voicelab-debug-androidTest.apk" >/dev/null
# Tối thiểu quyền: chỉ bộ nhận dạng mặc định (mạng) cần RECORD_AUDIO (thực nghiệm R1: lỗi 9 nếu thiếu).
if [ "$PROBE" = stt ] && [ "$ALLOW_NET" = 1 ] && [ "$REVOKE_MIC" = 0 ]; then
  "$ADB" shell pm grant "$PKG" android.permission.RECORD_AUDIO
  echo "   RECORD_AUDIO được cấp (bộ nhận dạng mặc định)"
else
  "$ADB" shell pm revoke "$PKG" android.permission.RECORD_AUDIO
  echo "   RECORD_AUDIO thu hồi"
fi

# --- 4. Chạy ------------------------------------------------------------------------------------------------------------
instrument() { # $1 = danh sách lớp test, phần còn lại = tham số -e
  local classes="$1"; shift
  local out="$EV/logs/$PROBE-$AVD-$STAMP"
  "$ADB" logcat -c
  : >"$out.jsonl"
  # Cố ý không dùng "set -e" ở đây: cần dọn log trước khi báo lỗi.
  local rc=0
  "$ADB" shell am instrument -w -e class "$classes" -e avd "$AVD" -e network_off "$NETOFF" \
    -e testDevice "$TESTDEV" "$@" "$RUNNER" >"$out.instr.txt" 2>&1 || rc=$?
  "$ADB" logcat -d -s HC_VOICE:I | grep -o '{.*}' >>"$out.jsonl" || true
  cat "$out.instr.txt"
  if [ "$rc" != 0 ] || ! grep -q '^OK (' "$out.instr.txt"; then
    echo "!! Bộ đo THẤT BẠI — xem $out.instr.txt" >&2
    return 1
  fi
  echo "   log HC_VOICE: $out.jsonl ($(wc -l <"$out.jsonl") dòng)"
}

run_args=()
[ -n "$RUNS" ] && run_args+=(-e runs "$RUNS")

pull_dir() { # $1 = thư mục trong files/ của app, $2 = đích; kéo từng tệp bằng run-as (app debug)
  mkdir -p "$2"
  local f
  "$ADB" shell "run-as $PKG ls files/$1 2>/dev/null" | tr -d '\r' | while IFS= read -r f; do
    "$ADB" exec-out "run-as $PKG cat files/$1/$f" >"$2/$f"
  done
}

push_dir() { # $1 = thư mục nguồn trên máy chủ, $2 = thư mục con trong files/
  local src="$1" dst="$2"
  "$ADB" shell "rm -rf $DEVICE_TMP && mkdir -p $DEVICE_TMP"
  "$ADB" push "$src"/. "$DEVICE_TMP"/ >/dev/null
  "$ADB" shell "run-as $PKG sh -c 'rm -rf files/$dst && mkdir -p files/$dst && cp $DEVICE_TMP/* files/$dst/'"
  "$ADB" shell "rm -rf $DEVICE_TMP"
}

case "$PROBE" in
  tts) instrument vn.hoicon.voicelab.TtsProbeTest,vn.hoicon.voicelab.TtsLatencyTest "${run_args[@]}" ;;
  clip) instrument vn.hoicon.voicelab.ClipLatencyTest "${run_args[@]}" ;;
  synth)
    "$ADB" shell "run-as $PKG rm -rf files/wav"
    instrument vn.hoicon.voicelab.SynthesizeTest
    pull_dir wav "$EV/wav"
    command -v ffmpeg >/dev/null || { echo "!! Thiếu ffmpeg để đổi WAV sang 16 kHz mono" >&2; exit 1; }
    for f in "$EV"/wav/*.wav; do
      ffmpeg -loglevel error -y -i "$f" -ar 16000 -ac 1 -sample_fmt s16 "$EV/wav16/$(basename "$f")"
    done
    echo "   WAV: $(ls "$EV"/wav/*.wav | wc -l) tệp → $EV/wav · 16 kHz mono: $(ls "$EV"/wav16/*.wav | wc -l) → $EV/wav16"
    ;;
  stt)
    instrument vn.hoicon.voicelab.SttProbeTest "${run_args[@]}"
    if [ -n "$SET" ]; then
      src="$EV/wav16"; [ "$SET" = team ] && src="$EV/audio/team"
      # Chỉ 20 câu chuẩn (a01…a12, s01…s08); tệp pause_*/hard_* chỉ để người nghe chấm.
      STAGE="$(mktemp -d)"
      cp "$src"/[as][0-9][0-9].wav "$STAGE"/ 2>/dev/null || true
      ls "$STAGE"/*.wav >/dev/null 2>&1 || { echo "BLOCKED: chưa có tệp WAV 16 kHz (a01…s08) ở $src" >&2; exit 3; }
      push_dir "$STAGE" "stt/$SET"
      net_args=(); [ "$ALLOW_NET" = 1 ] && net_args+=(-e allowNetwork true)
      [ "$CONFIRM_CLOUD" = 1 ] && net_args+=(-e confirmTeamCloud true)
      instrument vn.hoicon.voicelab.SttRunTest -e set "$SET" "${net_args[@]}"
      "$ADB" exec-out "run-as $PKG cat files/results/stt-$SET-$AVD.jsonl" >"$EV/logs/stt-$SET-$AVD-$STAMP.jsonl"
      echo "   kết quả nhận dạng: $EV/logs/stt-$SET-$AVD-$STAMP.jsonl"
    fi
    ;;
esac
echo "== xong ($PROBE, $AVD)"
