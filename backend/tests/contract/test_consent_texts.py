"""Hợp đồng văn bản đồng ý (spec 011): mỗi giá trị enum `Purpose` ↔ đúng 1 văn bản `docs/legal/consent/<purpose>.vi.md`,
sha256 trong manifest khớp chữ hiển thị, đổi chữ đã phát hành phải tăng phiên bản, chữ ấm áp/dễ đọc ở mức máy kiểm được,
DPIA nhắc đủ mọi mục đích, PILOT-PROTOCOL đủ mục. Không cần Postgres."""

import json
import re
from pathlib import Path
from typing import get_args

import pytest

from hoicon.api.routers.consents import Purpose
from hoicon.db.models import Consent
from hoicon.ops import consent_texts as ct

ROOT = Path(__file__).resolve().parents[3]
PURPOSES = tuple(get_args(Purpose))


def doc(text: str, *, extra: str = "") -> str:
    return f"# T\n> {ct.DRAFT_BANNER}\n\n{ct.BEGIN}\n{text}\n{ct.END}\n\n## Điểm chờ quyết\n- x\n{extra}"


GOOD = "Đây là trợ lý AI HỏiCon.\nHỏiCon xin phép bác một việc nhỏ.\nBác có thể tắt bất cứ lúc nào."


# ---------- tệp thật trong repo ----------


def test_repository_texts_have_no_problems() -> None:
    assert ct.problems() == []


def test_every_enum_value_has_exactly_one_text_and_no_extra_files() -> None:
    files = {p.name for p in ct.CONSENT_DIR.glob("*.vi.md")}
    assert files == {f"{p}.vi.md" for p in PURPOSES}


def test_manifest_lists_exactly_the_enum_values() -> None:
    manifest = ct.load_manifest()
    assert [e["purpose"] for e in manifest["purposes"]] == list(PURPOSES)


def test_schema_and_database_check_agree_with_the_enum() -> None:
    schema = json.loads((ROOT / "docs" / "schemas" / "consent_record.v1.json").read_text(encoding="utf-8"))
    enum = schema["properties"]["items"]["items"]["properties"]["purpose"]["enum"]
    assert set(enum) == set(PURPOSES)
    check = next(c for c in Consent.__table__.constraints if getattr(c, "name", None) and "purpose" in str(c.name))
    assert set(re.findall(r"'([a-z_]+)'", str(check.sqltext))) == set(PURPOSES)


def test_all_texts_are_drafts_pending_minh() -> None:
    for entry in ct.load_manifest()["purposes"]:
        assert entry["status"] == "draft"
        assert ct.DRAFT_BANNER in (ct.CONSENT_DIR / entry["file"]).read_text(encoding="utf-8")


def test_nothing_released_to_real_users_yet() -> None:
    assert ct.load_manifest()["released"] == []


# ---------- chuẩn hóa và băm ----------


def test_extract_text_ignores_blank_lines_trailing_spaces_and_notes_outside_markers() -> None:
    a = ct.extract_text(doc("Dòng một.  \n\n\nDòng hai."))
    b = ct.extract_text(doc("Dòng một.\nDòng hai.", extra="ghi chú thêm"))
    assert a == b == "Dòng một.\nDòng hai."
    assert ct.sha256_of(a) == ct.sha256_of(b)


def test_sha256_changes_when_one_character_changes() -> None:
    assert ct.sha256_of(ct.extract_text(doc("Bác ơi."))) != ct.sha256_of(ct.extract_text(doc("Bác ơi!")))


@pytest.mark.parametrize(
    "markdown",
    ["không có dấu", f"{ct.END}\nx\n{ct.BEGIN}", f"{ct.BEGIN}\nx", f"{ct.BEGIN}\na\n{ct.END}\n{ct.BEGIN}\nb\n{ct.END}"],
)
def test_extract_text_rejects_bad_markers(markdown: str) -> None:
    with pytest.raises(ValueError):
        ct.extract_text(markdown)


def test_sha256_matches_the_android_scheme() -> None:
    # Android băm UTF-8 của các chuỗi nối bằng "\n" (ConsentLedger.sha256Hex).
    assert ct.sha256_of("a\nb") == "7e18f737311b2dc3b2f269dd78396b0351f14fb66efa879f768cb23181883c78"
    assert (
        ct.sha256_of("Bác\nơi") == "a4b3fe26001c6da364dddc038bd44dfa4d473c6e7a48ea66177cb452062f97a4"
    )  # UTF-8, không NFD


# ---------- bất biến phiên bản ----------


def _entry(version: str = "2026.10-v3") -> dict[str, str]:
    return {"purpose": "lookups", "file": "lookups.vi.md", "version": version, "sha256": "x", "status": "draft"}


def test_released_text_changed_without_new_version_is_a_problem() -> None:
    released = [{"purpose": "lookups", "version": "2026.10-v3", "sha256": "a" * 64}]
    current = {"lookups": ("2026.10-v3", "b" * 64)}
    assert ct.released_problems(released, current)


def test_released_text_changed_with_new_version_is_fine() -> None:
    released = [{"purpose": "lookups", "version": "2026.10-v3", "sha256": "a" * 64}]
    assert ct.released_problems(released, {"lookups": ("2026.11-v4", "b" * 64)}) == []


def test_released_text_unchanged_is_fine() -> None:
    released = [{"purpose": "lookups", "version": "2026.10-v3", "sha256": "a" * 64}]
    assert ct.released_problems(released, {"lookups": ("2026.10-v3", "a" * 64)}) == []


def test_released_check_uses_recomputed_sha_not_the_manifest_claim(tmp_path: Path) -> None:
    root = _make_root(tmp_path, {"lookups": GOOD}, released=True)
    (root / "lookups.vi.md").write_text(doc(GOOD + "\nBác nhớ nhé."), encoding="utf-8")  # sửa chữ, KHÔNG sửa manifest
    assert any("phát hành" in p for p in ct.problems(root, ["lookups"]))


# ---------- luật chất lượng chữ ----------


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("Bác ơi.\n" + "từ " * 170, "từ"),
        ("Theo Điều 12 bác đồng ý.", "điều luật"),
        ("Theo Nghị định này bác đồng ý.", "điều luật"),
        ("Gọi số 0900000123 nhé bác.", "dãy số"),
        ("HỏiCon xin phép làm việc này.", "bác"),
        ("Bác sẽ mất hết tiền nếu không làm.", "hoảng"),
        ("Bác sẽ được hoàn tiền.", "hoàn tiền"),
        ("Đây là một câu " + "rất " * 45 + "dài, bác à.", "câu"),
    ],
)
def test_style_rules_flag_bad_wording(text: str, needle: str) -> None:
    assert any(needle in p for p in ct.style_problems(text, "drills")), text


def test_style_rules_accept_warm_short_text() -> None:
    assert ct.style_problems(GOOD, "drills") == []


@pytest.mark.parametrize(
    "exit_phrase",
    [
        "Bác tắt quyền này.",
        "Bác đổi ý bất cứ lúc nào.",
        "Bác chưa đồng ý cũng không sao.",
        "Bác từ chối cũng được.",
        "Muốn dừng, bác nhờ con bác.",
        "Bác rút lại lúc nào cũng được.",
    ],
)
def test_every_text_must_say_how_to_decline_or_stop(exit_phrase: str) -> None:
    """FR-006: người đọc phải biết mình từ chối/rút lại được (`lookups` từng mất câu này khi rút gọn cho đủ 160 từ)."""
    assert ct.style_problems(f"Bác ơi, HỏiCon xin phép làm việc này. {exit_phrase}", "overlay_pause") == []
    missing = ct.style_problems("Bác ơi, HỏiCon xin phép làm việc này giúp bác.", "overlay_pause")
    assert any("cách từ chối" in p for p in missing)


def test_ai_opening_required_only_for_ai_purposes() -> None:
    no_ai = "HỏiCon xin phép bác một việc nhỏ. Bác tắt được bất cứ lúc nào."
    assert any("Đây là trợ lý AI HỏiCon" in p for p in ct.style_problems(no_ai, "lookups"))
    assert ct.style_problems(no_ai, "overlay_pause") == []
    assert set(ct.AI_PURPOSES) <= set(PURPOSES)


# ---------- toàn bộ thư mục giả ----------


def _make_root(tmp: Path, texts: dict[str, str], *, released: bool = False) -> Path:
    root = tmp / "consent"
    root.mkdir()
    entries = []
    for purpose, text in texts.items():
        (root / f"{purpose}.vi.md").write_text(doc(text), encoding="utf-8")
        sha = ct.sha256_of(ct.extract_text(doc(text)))
        entries.append(
            {"purpose": purpose, "file": f"{purpose}.vi.md", "version": "2026.10-v3", "sha256": sha, "status": "draft"}
        )
    rel = (
        [{"purpose": e["purpose"], "version": e["version"], "sha256": e["sha256"]} for e in entries] if released else []
    )
    (root / "manifest.json").write_text(json.dumps({"released": rel, "purposes": entries}), encoding="utf-8")
    return root


def test_problems_detects_missing_extra_and_stale_sha(tmp_path: Path) -> None:
    root = _make_root(tmp_path, {"lookups": GOOD})
    assert ct.problems(root, ["lookups"]) == []
    assert any("drills" in p for p in ct.problems(root, ["lookups", "drills"]))  # thiếu văn bản
    (root / "extra.vi.md").write_text(doc(GOOD), encoding="utf-8")
    assert any("extra" in p for p in ct.problems(root, ["lookups"]))  # tệp thừa
    (root / "extra.vi.md").unlink()
    (root / "lookups.vi.md").write_text(doc(GOOD + "\nThêm."), encoding="utf-8")
    assert any("sha256" in p for p in ct.problems(root, ["lookups"]))  # chữ đổi, manifest cũ


def test_problems_detects_missing_banner_and_bad_version(tmp_path: Path) -> None:
    root = _make_root(tmp_path, {"lookups": GOOD})
    path = root / "lookups.vi.md"
    path.write_text(path.read_text(encoding="utf-8").replace(ct.DRAFT_BANNER, "đã duyệt"), encoding="utf-8")
    assert any("BẢN NHÁP" in p for p in ct.problems(root, ["lookups"]))
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["purposes"][0]["version"] = "v3"
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert any("phiên bản" in p for p in ct.problems(root, ["lookups"]))


def test_write_regenerates_sha_and_refuses_to_rewrite_released_text(tmp_path: Path) -> None:
    root = _make_root(tmp_path, {"lookups": GOOD})
    (root / "lookups.vi.md").write_text(doc(GOOD + "\nThêm một câu."), encoding="utf-8")
    ct.write(root, ["lookups"])
    assert ct.problems(root, ["lookups"]) == []
    other = tmp_path / "other"
    other.mkdir()
    released = _make_root(other, {"lookups": GOOD}, released=True)
    (released / "lookups.vi.md").write_text(doc(GOOD + "\nSửa lén."), encoding="utf-8")
    with pytest.raises(ValueError, match="phát hành"):
        ct.write(released, ["lookups"])


# ---------- DPIA và PILOT-PROTOCOL ----------


def test_dpia_mentions_every_purpose_and_the_unenforced_ones() -> None:
    dpia = (ROOT / "docs" / "PRIVACY-DPIA.md").read_text(encoding="utf-8")
    section = dpia.split("## 1. Mô tả xử lý", 1)[1].split("## 2.", 1)[0]
    # Cột đầu của bảng ở mục 1 phải liệt kê từng mục đích (một dòng có thể gộp nhiều mục đích cùng bản chất).
    in_table = {
        p
        for line in section.splitlines()
        if line.startswith("| `")
        for p in re.findall(r"`([a-z_]+)`", line.split("|")[1])
    }
    assert in_table == set(PURPOSES)
    assert "BẢN NHÁP" in dpia


@pytest.mark.parametrize(
    "needle",
    [
        "≥ 18",
        "2 lần/tháng",
        "hư cấu",
        "debrief",
        "rút lui",
        "xóa dữ liệu",
        "Kênh hỗ trợ",
        "BẢN NHÁP — chờ Minh duyệt",
        "khung giờ",
    ],
)
def test_pilot_protocol_has_required_sections(needle: str) -> None:
    text = (ROOT / "docs" / "PILOT-PROTOCOL.md").read_text(encoding="utf-8")
    assert needle in text


def test_pilot_protocol_placeholder_only_while_draft() -> None:
    text = (ROOT / "docs" / "PILOT-PROTOCOL.md").read_text(encoding="utf-8")
    if "[CHỜ MINH ĐIỀN" in text:
        assert "BẢN NHÁP — chờ Minh duyệt" in text
