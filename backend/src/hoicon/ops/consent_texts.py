"""Văn bản đồng ý theo từng mục đích (spec 011): trích chữ hiển thị, băm sha256, đối chiếu `manifest.json`.

    python -m hoicon.ops.consent_texts check    # in vấn đề (nếu có), thoát 1 khi có
    python -m hoicon.ops.consent_texts write    # tính lại sha256 vào manifest.json (không đụng chữ)

Quy tắc băm (khớp `ConsentLedger.sha256Hex` của Android: băm UTF-8 của các chuỗi hiển thị nối bằng "\\n"):
chữ hiển thị là các dòng khác rỗng nằm giữa `<!-- BEGIN-TEXT -->` và `<!-- END-TEXT -->`, bỏ khoảng trắng cuối
dòng, nối bằng "\\n". Ghi chú
soạn thảo ngoài hai dấu đó KHÔNG vào sha256, nên sửa ghi chú không làm đổi bằng chứng đã ghi vào bảng `consents`.

Bất biến phiên bản (CLAUDE.md luật 7): `released` liệt kê các cặp (mục đích, phiên bản, sha256) đã đưa cho người
thật. Chữ của
một cặp đã phát hành mà đổi thì phải tăng phiên bản. Mô-đun này không in số điện thoại, không gọi mạng, không đụng DB.
"""

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, get_args

from hoicon.eval.checks import PANIC_PHRASES, REFUND_PHRASES

ROOT = Path(__file__).resolve().parents[4]
CONSENT_DIR = ROOT / "docs" / "legal" / "consent"
BEGIN = "<!-- BEGIN-TEXT -->"
END = "<!-- END-TEXT -->"
DRAFT_BANNER = "BẢN NHÁP — chờ Minh duyệt"
AI_OPENING = "Đây là trợ lý AI HỏiCon"
DECISIONS_HEADING = "## Điểm chờ quyết"
DEFAULT_VERSION = "2026.10-v3"
VERSION_RE = re.compile(r"^\d{4}\.\d{2}-v\d+$")
MAX_VERSION_LEN = 16  # cột consents.consent_version
STATUSES = ("draft", "approved")
# Văn bản nói về việc AI xử lý hay tương tác với người dùng: mở đầu bằng câu công khai AI (CLAUDE.md luật 6).
AI_PURPOSES = frozenset({"core_protection", "guardian_alerts", "llm_processing", "voice_input", "drills", "lookups"})
MAX_WORDS = 160
MAX_AVG_SENTENCE_WORDS = 25
MAX_SENTENCE_WORDS = 40
_LAW = re.compile(r"Điều\s*\d|Nghị định|Thông tư|Khoản\s*\d|Luật\s+(?:số|bảo|trí)", re.IGNORECASE)
_LONG_DIGITS = re.compile(r"\d{4,}")
_SENTENCE_END = re.compile(r"[.!?]+")
# Cụm cho biết người đọc từ chối/rút/tắt/dừng được. Cố ý KHÔNG tính chữ "nhờ" (xuất hiện ở "khi bác nhờ" nghĩa khác).
_EXIT = re.compile(r"tắt|rút|đổi ý|chưa đồng ý|từ chối|muốn dừng|dừng giữa chừng", re.IGNORECASE)


def purposes() -> tuple[str, ...]:
    """Giá trị enum đồng ý của máy chủ (nguồn duy nhất; thêm giá trị mà quên văn bản ⇒ `check` thất bại)."""
    from hoicon.api.routers.consents import Purpose

    return tuple(get_args(Purpose))


def extract_text(markdown: str) -> str:
    """Chữ hiển thị chuẩn hóa. Đúng một cặp dấu BEGIN/END theo thứ tự, ngược lại ValueError."""
    if markdown.count(BEGIN) != 1 or markdown.count(END) != 1 or markdown.index(BEGIN) > markdown.index(END):
        raise ValueError(f"cần đúng một cặp {BEGIN} … {END}")
    body = markdown.split(BEGIN, 1)[1].split(END, 1)[0]
    return "\n".join(line.rstrip() for line in body.splitlines() if line.strip())


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(root: Path = CONSENT_DIR) -> dict[str, Any]:
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def style_problems(text: str, purpose: str) -> list[str]:
    """Luật chất lượng chữ ở mức máy kiểm được (ấm áp thật sự thuộc `ux-elder-reviewer`). Danh sách rỗng = đạt."""
    out: list[str] = []
    words = text.split()
    if len(words) > MAX_WORDS:
        out.append(f"{purpose}: {len(words)} từ (tối đa {MAX_WORDS}): quá dài cho người cao tuổi")
    sentences = [s.split() for s in _SENTENCE_END.split(text.replace("\n", ". ")) if s.strip()]
    if sentences:
        average = sum(len(s) for s in sentences) / len(sentences)
        if average > MAX_AVG_SENTENCE_WORDS:
            out.append(f"{purpose}: câu trung bình {average:.0f} từ (tối đa {MAX_AVG_SENTENCE_WORDS})")
        longest = max(len(s) for s in sentences)
        if longest > MAX_SENTENCE_WORDS:
            out.append(f"{purpose}: có câu dài {longest} từ (tối đa {MAX_SENTENCE_WORDS})")
    if _LAW.search(text):
        out.append(f"{purpose}: có điều luật/văn bản pháp lý (chưa có nguồn đã kiểm, người cao tuổi cũng không cần)")
    if _LONG_DIGITS.search(text):
        out.append(f"{purpose}: có dãy số ≥ 4 chữ số (giống số điện thoại/tài khoản)")
    if not _EXIT.search(text):
        out.append(f"{purpose}: không nói cách từ chối/rút lại/tắt (FR-006: người đọc phải biết mình thoát được)")
    if "bác" not in text.lower():
        out.append(f"{purpose}: không xưng 'bác' (Hiến chương VI)")
    lowered = text.lower()
    for phrase in PANIC_PHRASES:
        if phrase in lowered:
            out.append(f"{purpose}: cụm gây hoảng sợ '{phrase}'")
    for phrase in REFUND_PHRASES:
        if phrase in lowered:
            out.append(f"{purpose}: hứa hoàn tiền '{phrase}'")
    if purpose in AI_PURPOSES and not text.startswith(AI_OPENING):
        out.append(f"{purpose}: phải mở đầu bằng '{AI_OPENING}' (CLAUDE.md luật 6)")
    return out


def released_problems(released: Sequence[Mapping[str, str]], current: Mapping[str, tuple[str, str]]) -> list[str]:
    """`current`: mục đích → (phiên bản, sha256 TÍNH LẠI từ chữ). Chữ đã phát hành mà đổi, giữ phiên bản ⇒ vấn đề."""
    out: list[str] = []
    for entry in released:
        version, sha = current.get(entry["purpose"], (None, None))
        if version == entry["version"] and sha != entry["sha256"]:
            out.append(
                f"{entry['purpose']}: chữ của phiên bản {version} đã phát hành nhưng bị đổi — phải tăng phiên bản"
            )
    return out


def problems(root: Path = CONSENT_DIR, purpose_list: Sequence[str] | None = None) -> list[str]:
    wanted = list(purpose_list) if purpose_list is not None else list(purposes())
    out: list[str] = []
    try:
        manifest = load_manifest(root)
    except (OSError, ValueError) as exc:
        return [f"không đọc được manifest.json: {type(exc).__name__}"]
    entries = {e["purpose"]: e for e in manifest.get("purposes", [])}
    files = {p.name for p in root.glob("*.vi.md")}
    for name in sorted(files - {f"{p}.vi.md" for p in wanted}):
        out.append(f"{name}: tệp thừa (không có mục đích tương ứng trong enum)")
    for extra in sorted(entries.keys() - set(wanted)):
        out.append(f"{extra}: có trong manifest nhưng không có trong enum")
    current: dict[str, tuple[str, str]] = {}
    for purpose in wanted:
        entry = entries.get(purpose)
        path = root / f"{purpose}.vi.md"
        if not path.is_file():
            out.append(f"{purpose}: thiếu văn bản {path.name}")
            continue
        if entry is None:
            out.append(f"{purpose}: thiếu trong manifest.json")
            continue
        markdown = path.read_text(encoding="utf-8")
        try:
            text = extract_text(markdown)
        except ValueError as exc:
            out.append(f"{purpose}: {exc}")
            continue
        sha = sha256_of(text)
        current[purpose] = (entry["version"], sha)
        if entry.get("file") != path.name:
            out.append(f"{purpose}: manifest trỏ tới tệp '{entry.get('file')}', mong {path.name}")
        if entry["sha256"] != sha:
            out.append(f"{purpose}: sha256 trong manifest không khớp chữ hiển thị (chạy `consent_texts write`)")
        if not VERSION_RE.match(entry["version"]) or len(entry["version"]) > MAX_VERSION_LEN:
            out.append(f"{purpose}: phiên bản '{entry['version']}' sai dạng YYYY.MM-vN hoặc dài quá {MAX_VERSION_LEN}")
        if entry["status"] not in STATUSES:
            out.append(f"{purpose}: trạng thái '{entry['status']}' không thuộc {STATUSES}")
        if entry["status"] == "draft":
            if DRAFT_BANNER not in markdown:
                out.append(f"{purpose}: thiếu dòng '{DRAFT_BANNER}' (trạng thái draft)")
        elif DRAFT_BANNER in markdown:
            out.append(f"{purpose}: đã approved nhưng vẫn còn dòng '{DRAFT_BANNER}'")
        if DECISIONS_HEADING not in markdown:
            out.append(f"{purpose}: thiếu mục '{DECISIONS_HEADING}' cho người duyệt")
        out.extend(style_problems(text, purpose))
    out.extend(released_problems(manifest.get("released", []), current))
    return out


def write(root: Path = CONSENT_DIR, purpose_list: Sequence[str] | None = None) -> dict[str, Any]:
    """Tính lại sha256 từng văn bản và ghi manifest.json. Giữ phiên bản/trạng thái đã có; từ chối nếu chữ của một cặp
    đã phát hành bị đổi mà chưa tăng phiên bản (để không ghi đè bằng chứng)."""
    wanted = list(purpose_list) if purpose_list is not None else list(purposes())
    old = {}
    released: list[dict[str, str]] = []
    if (root / "manifest.json").is_file():
        previous = load_manifest(root)
        old = {e["purpose"]: e for e in previous.get("purposes", [])}
        released = list(previous.get("released", []))
    entries: list[dict[str, str]] = []
    current: dict[str, tuple[str, str]] = {}
    for purpose in wanted:
        sha = sha256_of(extract_text((root / f"{purpose}.vi.md").read_text(encoding="utf-8")))
        version = old.get(purpose, {}).get("version", DEFAULT_VERSION)
        status = old.get(purpose, {}).get("status", "draft")
        file = f"{purpose}.vi.md"
        entries.append({"purpose": purpose, "file": file, "version": version, "sha256": sha, "status": status})
        current[purpose] = (version, sha)
    blocked = released_problems(released, current)
    if blocked:
        raise ValueError("; ".join(blocked))
    manifest = {"version_scheme": "YYYY.MM-vN", "released": released, "purposes": entries}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Văn bản đồng ý theo mục đích (spec 011)")
    parser.add_argument("command", choices=("check", "write"))
    command = parser.parse_args(argv).command
    if command == "write":
        try:
            manifest = write()
        except (OSError, ValueError) as exc:
            print(f"Lỗi: {exc}", file=sys.stderr)
            return 1
        print(f"Đã ghi manifest.json: {len(manifest['purposes'])} văn bản.")
    found = problems()
    for problem in found:
        print(f"- {problem}", file=sys.stderr)
    if found:
        print(f"{len(found)} vấn đề.", file=sys.stderr)
        return 1
    print(f"Đạt: {len(purposes())} mục đích ↔ {len(purposes())} văn bản, sha256 khớp.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
