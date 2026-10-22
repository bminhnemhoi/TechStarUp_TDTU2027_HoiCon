"""Chốt chặn phát hành (spec 011 T019, FR-003/SC-006): ba mục đích hứa điều mã chưa làm chỉ được "phát hành"
khi đã có test thực thi lời hứa. Chạy trong CI mọi PR nên không ai đánh dấu phát hành khi lời hứa chưa có mã."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from hoicon.ops import consent_texts as ct

PROMISE_PURPOSES = ("llm_processing", "voice_input", "pilot_research")
INTEGRATION = Path(__file__).resolve().parents[1] / "integration"


def release_block_problems(manifest: Mapping[str, Any], tests_dir: Path) -> list[str]:
    """Mục đích hứa-chưa-có-mã mà có mặt trong `released` hoặc `status: approved` nhưng thiếu tệp test thực thi."""
    released = {str(e.get("purpose")) for e in manifest.get("released", [])}
    approved = {str(e.get("purpose")) for e in manifest.get("purposes", []) if e.get("status") == "approved"}
    out: list[str] = []
    for purpose in PROMISE_PURPOSES:
        if purpose not in released | approved:
            continue
        if not (tests_dir / f"test_consent_enforcement_{purpose}.py").is_file():
            out.append(f"{purpose}: phát hành/approved nhưng thiếu test_consent_enforcement_{purpose}.py")
    return out


def _manifest(released: Sequence[str] = (), approved: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "released": [{"purpose": p} for p in released],
        "purposes": [{"purpose": p, "status": "approved" if p in approved else "draft"} for p in PROMISE_PURPOSES],
    }


def test_real_manifest_does_not_release_unfulfilled_promises() -> None:
    assert release_block_problems(ct.load_manifest(), INTEGRATION) == []


def test_released_promise_without_enforcement_test_is_rejected(tmp_path: Path) -> None:
    problems = release_block_problems(_manifest(released=["llm_processing"]), tmp_path)
    assert len(problems) == 1 and "llm_processing" in problems[0]


def test_approved_promise_without_enforcement_test_is_rejected(tmp_path: Path) -> None:
    problems = release_block_problems(_manifest(approved=["voice_input"]), tmp_path)
    assert len(problems) == 1 and "voice_input" in problems[0]


def test_promise_with_enforcement_test_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "test_consent_enforcement_pilot_research.py").write_text("", encoding="utf-8")
    assert release_block_problems(_manifest(released=["pilot_research"]), tmp_path) == []


def test_other_purposes_are_not_blocked(tmp_path: Path) -> None:
    manifest = {"released": [{"purpose": "core_protection"}], "purposes": []}
    assert release_block_problems(manifest, tmp_path) == []
