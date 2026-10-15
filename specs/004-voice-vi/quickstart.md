# Quickstart: kiểm tay spec 004 (worktree `../hoicon-wt/android`)

```bash
cd ~/Projects/hoicon-wt/android
source scripts/android-env.sh
EV=~/hoicon-evidence/004-voice-vi        # ngoài repo; voice-lab.sh tự tạo, quyền 700

# Script + dữ liệu (không cần máy ảo)
python3 -m unittest discover -s scripts/tests

# Dựng bộ đo
apps/android/gradlew -p apps/android :voicelab:assembleDebug :voicelab:lintDebug :voicelab:testDebugUnitTest

# Máy ảo: MỘT AVD mỗi lúc; kiểm `free -m` (cột available ≥ 5 GB), `gradlew --stop` nếu thiếu RAM.
# --headless = -no-audio (không mở micro máy chủ; probe stt đòi điều này). docs/EMULATOR.md §1.2 nếu TTS vi-VN hỏng.
bash scripts/emu-start.sh hc-api36 --headless
bash scripts/voice-lab.sh --avd hc-api36 --probe tts          # bảng giọng + độ trễ nguội/ấm (mạng tắt)
bash scripts/voice-lab.sh --avd hc-api36 --probe clip
bash scripts/voice-lab.sh --avd hc-api36 --probe synth        # WAV về $EV/wav, 16 kHz mono về $EV/wav16
bash scripts/voice-lab.sh --avd hc-api36 --probe stt                       # chỉ thăm dò hỗ trợ vi-VN
bash scripts/voice-lab.sh --avd hc-api36 --probe stt --set synthetic       # nhận dạng 20 câu tổng hợp
# Máy ảo không có vi-VN trên máy (vd. hc-api34): BLOCKED trừ khi đo bộ nhận dạng mặc định (dùng mạng, nhãn "không dùng cho sản phẩm"):
#   bash scripts/voice-lab.sh --avd hc-api34 --probe stt --set synthetic --allow-network
# Bản thu của đội (xem dưới), chỉ trên bộ nhận dạng TRÊN MÁY; qua bộ nhận dạng mạng chỉ khi người thu đã biết âm thanh
# có thể gửi tới Google: thêm --allow-network --confirm-team-audio-to-cloud
bash scripts/voice-lab.sh --avd hc-api36 --probe stt --set team
adb emu kill                                                   # tắt hẳn rồi mới bật AVD khác (hc-api34)

# Bản thu của đội (Tiến tự thu, ≥ 18 tuổi, đồng ý bằng lời): đọc 20 câu trong data/voice/sentences.v1.json,
# đặt tên theo id câu (a01.m4a … s08.m4a) trong $EV/audio/team rồi đổi định dạng:
for f in $EV/audio/team/*.m4a; do ffmpeg -loglevel error -y -i "$f" -ar 16000 -ac 1 -sample_fmt s16 "${f%.m4a}.wav"; done

# WER + ý định: chỉ tệp KẾT QUẢ (stt-<bộ>-<avd>-<giờ>.jsonl), không phải log thăm dò stt-<avd>-*.jsonl.
# Nhiều lượt cùng AVD/bộ sẽ bị gộp: truyền đúng tệp của lượt cần dùng thay cho dấu *.
python3 scripts/voice-wer.py --sentences data/voice/sentences.v1.json \
  --results $EV/logs/stt-synthetic-hc-api36-*.jsonl $EV/logs/stt-synthetic-hc-api34-*.jsonl --out $EV/wer
```
Ghi mọi số vào `evidence.md` (nhãn máy ảo/máy thật + n). Xóa `$EV/audio/` sau 10/01/2027.
