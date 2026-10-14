#!/usr/bin/env python3
"""Sinh danh mục app tài chính cho Android từ data/bank_apps.vn.json (một nguồn sự thật, P1-S2).

Ghi đè:
  - apps/android/rules/src/main/kotlin/vn/hoicon/rules/BankAppCatalog.kt  (luật R1 khớp ĐÚNG tên gói)
  - khối <queries> giữa hai dấu BEGIN/END trong apps/android/app/src/main/AndroidManifest.xml

`:rules:test` (BankAppCatalogTest) báo lỗi nếu quên chạy lại script sau khi sửa JSON.

    python scripts/gen-bank-apps.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "bank_apps.vn.json"
CATALOG = ROOT / "apps/android/rules/src/main/kotlin/vn/hoicon/rules/BankAppCatalog.kt"
MANIFEST = ROOT / "apps/android/app/src/main/AndroidManifest.xml"
BEGIN = "<!-- BEGIN bank_apps: sinh bởi scripts/gen-bank-apps.py, không sửa tay -->"
END = "<!-- END bank_apps -->"
CATEGORY = {"bank": "BANK", "wallet": "WALLET", "securities": "SECURITIES"}


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    apps = sorted(data["apps"], key=lambda a: (a["category"], a["package"]))
    packages = [a["package"] for a in apps]
    if len(packages) != len(set(packages)):
        sys.exit("package trùng lặp trong data/bank_apps.vn.json")

    entries = "\n".join(
        f'        "{a["package"]}" to AppCategory.{CATEGORY[a["category"]]},'
        for a in apps
    )
    CATALOG.write_text(
        f"""// SINH TỰ ĐỘNG bởi scripts/gen-bank-apps.py từ data/bank_apps.vn.json — không sửa tay.
package vn.hoicon.rules

/**
 * Financial apps that arm rule R1 ({len(apps)} packages, list version [VERSION]). EXACT package match only:
 * `com.vnpay.*` is shared by several banks and a wallet. The same packages are declared in `<queries>`
 * (AndroidManifest.xml) — without that, UsageStats hides them from us on API 30+.
 */
object BankAppCatalog {{
    const val VERSION = "{data["version"]}"

    private val categories: Map<String, AppCategory> = mapOf(
{entries}
    )

    val packages: Set<String> get() = categories.keys

    fun categoryOf(packageName: String): AppCategory? = categories[packageName]
}}
""",
        encoding="utf-8",
        newline="\n",
    )

    manifest = MANIFEST.read_text(encoding="utf-8")
    block = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if not block.search(manifest):
        sys.exit(f"không thấy dấu {BEGIN!r} trong {MANIFEST}")
    queries = "\n".join(f'        <package android:name="{p}" />' for p in packages)
    manifest = block.sub(lambda _: f"{BEGIN}\n{queries}\n        {END}", manifest)
    MANIFEST.write_text(manifest, encoding="utf-8", newline="\n")
    print(
        f"{len(apps)} app ({data['version']}) ⇒ {CATALOG.relative_to(ROOT)} + <queries>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
