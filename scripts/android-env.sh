# Nạp (source) bởi emu-start.sh / avd-create.sh / setup-android.sh: xác định SDK, JDK, AVD theo hệ điều hành.
# Ưu tiên biến môi trường đã có; mặc định: Windows (Git Bash) D:/Android, Linux/macOS ~/Android.
case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*) HC_OS=windows; EXE=.exe; BAT=.bat; ANDROID_ROOT="${ANDROID_ROOT:-D:/Android}" ;;
  Darwin) HC_OS=macos; EXE=; BAT=; ANDROID_ROOT="${ANDROID_ROOT:-$HOME/Android}" ;;
  *) HC_OS=linux; EXE=; BAT=; ANDROID_ROOT="${ANDROID_ROOT:-$HOME/Android}" ;;
esac
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$ANDROID_ROOT/Sdk}}"
if [ "$HC_OS" = windows ]; then
  AVD_HOME_DEFAULT="$ANDROID_ROOT/avd"
else
  AVD_HOME_DEFAULT="$HOME/.android/avd"
fi
export ANDROID_HOME="$SDK" ANDROID_SDK_ROOT="$SDK" ANDROID_AVD_HOME="${ANDROID_AVD_HOME:-$AVD_HOME_DEFAULT}"
JDK_DIR="${HOICON_JDK:-$ANDROID_ROOT/jdk-21}"
ADB="$SDK/platform-tools/adb$EXE"
EMU="$SDK/emulator/emulator$EXE"
ACLI="$SDK/cmdline-tools/latest/bin/android$EXE"
