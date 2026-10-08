# Đặt biến môi trường cấp NGƯỜI DÙNG cho toolchain Android của HỏiCon (không cần quyền admin, idempotent).
#   powershell -ExecutionPolicy Bypass -File scripts\env-android.ps1
# Sau khi chạy: mở terminal / VS Code mới để nhận biến. Xem docs/EMULATOR.md.
$ErrorActionPreference = 'Stop'

$Sdk = 'D:\Android\Sdk'
$Vars = @{
  ANDROID_HOME     = $Sdk
  ANDROID_SDK_ROOT = $Sdk
  ANDROID_AVD_HOME = 'D:\Android\avd'
  GRADLE_USER_HOME = 'D:\.gradle'
}
foreach ($k in $Vars.Keys) {
  [Environment]::SetEnvironmentVariable($k, $Vars[$k], 'User')
  Write-Host "set $k=$($Vars[$k])"
}

# PATH người dùng: thêm platform-tools (adb), emulator, cmdline-tools (android CLI) nếu chưa có.
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$parts = @($userPath -split ';' | Where-Object { $_ })
foreach ($p in @("$Sdk\platform-tools", "$Sdk\emulator", "$Sdk\cmdline-tools\latest\bin")) {
  if ($parts -notcontains $p) { $parts += $p; Write-Host "PATH += $p" }
}
[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')

# Gradle dùng JDK 21 (AGP chưa hỗ trợ JDK 25 đang là JAVA_HOME). Ghi vào gradle.properties của
# GRADLE_USER_HOME (theo máy, ngoài repo) thay vì gradle.properties của dự án.
$Jdk = 'D:\Android\jdk-21'
$GradleProps = 'D:\.gradle\gradle.properties'
New-Item -ItemType Directory -Force (Split-Path $GradleProps) | Out-Null
$line = 'org.gradle.java.home=' + ($Jdk -replace '\\', '/')
$existing = if (Test-Path $GradleProps) { @(Get-Content $GradleProps) } else { @() }
$kept = @($existing | Where-Object { $_ -notmatch '^org\.gradle\.java\.home=' })
Set-Content -Path $GradleProps -Value (@($kept) + $line) -Encoding ascii
Write-Host "$GradleProps : $line"

Write-Host 'Xong. Mở terminal mới rồi kiểm tra:  adb version ; emulator -list-avds'
