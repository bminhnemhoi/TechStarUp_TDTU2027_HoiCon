"""Kiểm tra scripts/release-gate.sh (spec 029 FR-005) — python3 -m unittest scripts/tests/test_release_gate.py

Cần APK debug (`./apps/android/gradlew -p apps/android :app:assembleDebug`) và Android SDK; thiếu thì test tương ứng
được BỎ QUA có nêu lý do (không bao giờ tính là đạt).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "release-gate.sh"
_DEBUG_APK = _ROOT / "apps" / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
_HOOK = _ROOT / ".claude" / "hooks" / "guard-privacy.mjs"
_SDK = Path(os.environ.get("ANDROID_HOME") or Path.home() / "Android" / "Sdk")


def _run(*args: str, skip_pin: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if skip_pin:  # bước ConsentTextsPinTest chạy Gradle: không lồng Gradle vào unit test của script
        env["HC_GATE_SKIP_PIN_TEST"] = "1"
    return subprocess.run(["bash", str(_SCRIPT), *args], capture_output=True, text=True, check=False, timeout=300, env=env)


def _line(output: str, title: str) -> str:
    """Dòng kết quả của một mục, ví dụ _line(out, "R8") ⇒ "[TRƯỢT]    R8: …"."""
    for line in output.splitlines():
        if re.match(rf"^\[[^\]]+\]\s+{re.escape(title)}:", line):
            return line
    raise AssertionError(f"không có mục {title!r} trong:\n{output}")


def _aapt2() -> Path | None:
    found = sorted((_SDK / "build-tools").glob("*/aapt2"), key=lambda p: [int(x) for x in re.findall(r"\d+", p.parent.name)])
    return found[-1] if found else None


def _android_jar() -> Path | None:
    found = sorted((_SDK / "platforms").glob("android-*/android.jar"))
    return found[-1] if found else None


class UsageTest(unittest.TestCase):
    def test_no_args_prints_usage_and_exits_2(self) -> None:
        proc = _run()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("release-gate.sh", proc.stderr)

    def test_missing_file_exits_2(self) -> None:
        proc = _run("/khong/co/app.apk")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Không thấy tệp", proc.stderr)

    def test_other_extensions_are_refused(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            proc = _run(tmp.name)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(".apk hoặc .aab", proc.stderr)


@unittest.skipUnless(_DEBUG_APK.exists(), f"chưa dựng APK debug: {_DEBUG_APK} (chạy :app:assembleDebug)")
class DebugApkTest(unittest.TestCase):
    """Bản debug không được phát hành: cổng phải TRƯỢT, nói rõ vì sao, và vẫn xác nhận phần quyền sạch."""

    proc: subprocess.CompletedProcess[str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.proc = _run(str(_DEBUG_APK))

    def test_exits_non_zero(self) -> None:
        self.assertEqual(self.proc.returncode, 1, self.proc.stdout + self.proc.stderr)
        self.assertIn("không phát hành", self.proc.stdout)

    def test_r8_fails_with_a_diagnostic(self) -> None:
        line = _line(self.proc.stdout, "R8")
        self.assertTrue(line.startswith("[TRƯỢT]"), line)
        self.assertRegex(line, r"\d+/\d+ lớp")  # log chẩn đoán: bao nhiêu lớp có tên rút gọn
        self.assertIn("proguard", self.proc.stdout)  # gợi ý sửa

    def test_forbidden_permissions_pass(self) -> None:
        self.assertTrue(_line(self.proc.stdout, "Quyền cấm").startswith("[ĐẠT]"), self.proc.stdout)

    def test_other_debug_leftovers_are_reported(self) -> None:
        self.assertTrue(_line(self.proc.stdout, "Debuggable").startswith("[TRƯỢT]"))
        self.assertTrue(_line(self.proc.stdout, "Nhật ký spike").startswith("[TRƯỢT]"))
        self.assertTrue(_line(self.proc.stdout, "Cleartext").startswith("[TRƯỢT]"))

    def test_ai_disclosure_passes(self) -> None:
        self.assertTrue(_line(self.proc.stdout, "Công khai AI").startswith("[ĐẠT]"))

    def test_manual_items_are_listed(self) -> None:
        self.assertEqual(self.proc.stdout.count("[KIỂM TAY]"), 2)

    def test_skipping_the_pin_test_never_turns_the_gate_green(self) -> None:
        line = _line(self.proc.stdout, "ConsentTextsPinTest")
        self.assertTrue(line.startswith("[BỎ QUA]"), line)


@unittest.skipUnless(_aapt2() and _android_jar(), f"thiếu aapt2/android.jar trong {_SDK}")
class ForbiddenPermissionsTest(unittest.TestCase):
    """Dựng APK nhỏ chỉ có manifest để thấy mục quyền thật sự bắt được quyền cấm (và không báo oan)."""

    def _gate_for(self, body: str) -> str:
        aapt2, jar = _aapt2(), _android_jar()
        assert aapt2 and jar
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        manifest = tmp / "AndroidManifest.xml"
        manifest.write_text(
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="vn.hoicon.gatefixture">'
            f"{body}</manifest>",
            encoding="utf-8",
        )
        apk = tmp / "fixture.apk"
        subprocess.run([str(aapt2), "link", "-o", str(apk), "--manifest", str(manifest), "-I", str(jar)], check=True, capture_output=True)
        return _run(str(apk)).stdout

    def test_clean_manifest_passes_the_permission_item(self) -> None:
        out = self._gate_for('<uses-permission android:name="android.permission.INTERNET"/><application/>')
        self.assertTrue(_line(out, "Quyền cấm").startswith("[ĐẠT]"), out)

    def test_each_forbidden_permission_from_the_task_is_caught(self) -> None:
        for name in ("CAMERA", "READ_SMS", "READ_CALL_LOG", "READ_CONTACTS"):
            with self.subTest(name):
                out = self._gate_for(f'<uses-permission android:name="android.permission.{name}"/><application/>')
                line = _line(out, "Quyền cấm")
                self.assertTrue(line.startswith("[TRƯỢT]"), line)
                self.assertIn(f"android.permission.{name}", line)

    def test_a_forbidden_service_is_caught_without_a_uses_permission(self) -> None:
        out = self._gate_for(
            '<application><service android:name=".Watcher" '
            'android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"/></application>'
        )
        line = _line(out, "Quyền cấm")
        self.assertTrue(line.startswith("[TRƯỢT]"), line)
        self.assertIn("BIND_ACCESSIBILITY_SERVICE", line)


class ForbiddenListTest(unittest.TestCase):
    """Danh sách của cổng luôn chứa danh sách của hook guard-privacy (không để hai nơi lệch nhau)."""

    def test_gate_list_contains_the_hook_list(self) -> None:
        hook = _HOOK.read_text(encoding="utf-8")
        block = re.search(r"const FORBIDDEN = \[(.*?)\];", hook, re.S)
        self.assertIsNotNone(block, "guard-privacy.mjs đổi cấu trúc: cập nhật test này")
        assert block
        hook_names = set(re.findall(r'"(android\.permission\.[A-Z_]+)"', block.group(1)))
        self.assertGreaterEqual(len(hook_names), 10)
        gate = _SCRIPT.read_text(encoding="utf-8")
        gate_names = set(re.findall(r"^\s+(android\.permission\.[A-Z_]+)$", gate, re.M))
        self.assertEqual(sorted(hook_names - gate_names), [], "release-gate.sh thiếu quyền mà hook đang cấm")
        for extra in ("CAMERA", "READ_SMS", "READ_CALL_LOG", "READ_CONTACTS"):
            self.assertIn(f"android.permission.{extra}", gate_names)


if __name__ == "__main__":
    unittest.main()
