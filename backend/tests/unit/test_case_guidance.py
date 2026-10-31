"""Spec 031 FR-015 (T019): `load_guidance()` đọc YAML một lần và kiểm cấu trúc ngay lúc nạp."""

from pathlib import Path

import pytest

from hoicon.services import case_file_service as svc

STEPS = [
    {"id": "contact_bank", "text_vi": "Gọi tổng đài ghi sau thẻ của ngân hàng người thân.", "source_ref": None},
    {"id": "contact_police", "text_vi": "Mang bản hồ sơ này tới công an phường hoặc xã.", "source_ref": "Nguồn thử"},
]


def write(tmp: Path, text: str) -> Path:
    path = tmp / "guidance.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def doc(approved: bool, steps: list[dict] | None = None, fallback: str = "Anh/chị liên hệ công an nơi cư trú.") -> dict:
    return {"approved": approved, "fallback_vi": fallback, "steps": STEPS if steps is None else steps}


def test_the_shipped_file_is_valid_and_unapproved_so_it_exposes_no_steps() -> None:
    svc.load_guidance.cache_clear()
    guidance = svc.load_guidance()
    assert guidance["approved"] is False and guidance["steps"] == [] and len(guidance["fallback_vi"]) >= 10


def test_an_unapproved_file_never_leaks_its_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import yaml

    monkeypatch.setattr(svc, "GUIDANCE_FILE", write(tmp_path, yaml.safe_dump(doc(False), allow_unicode=True)))
    svc.load_guidance.cache_clear()
    assert svc.load_guidance()["steps"] == []
    svc.load_guidance.cache_clear()


def test_an_approved_file_keeps_every_step_in_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import yaml

    monkeypatch.setattr(svc, "GUIDANCE_FILE", write(tmp_path, yaml.safe_dump(doc(True), allow_unicode=True)))
    svc.load_guidance.cache_clear()
    guidance = svc.load_guidance()
    assert [s["id"] for s in guidance["steps"]] == ["contact_bank", "contact_police"]
    assert guidance["steps"][1]["source_ref"] == "Nguồn thử"
    svc.load_guidance.cache_clear()


@pytest.mark.parametrize(
    "bad",
    [
        doc(True, fallback="ngắn"),  # fallback_vi quá ngắn
        doc(True, steps=[{**STEPS[0], "id": "Sai Id"}]),  # id sai mẫu
        doc(True, steps=[{**STEPS[0], "text_vi": "ngắn"}]),  # text_vi < 10 ký tự
        doc(
            True, steps=[{**STEPS[0], "text_vi": "Gọi ngay 1900 1234 để hỏi."}]
        ),  # dãy ≥ 4 chữ số (số đường dây chưa kiểm)
        doc(True, steps=[{**STEPS[0], "id": f"step_{i}"} for i in range(9)]),  # > 8 bước
        doc(True, steps=[STEPS[0], STEPS[0]]),  # trùng id
        {
            "approved": "yes",
            "fallback_vi": "Anh/chị liên hệ công an nơi cư trú.",
            "steps": [],
        },  # approved không phải bool
    ],
)
def test_a_malformed_file_is_rejected_at_load(bad: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import yaml

    monkeypatch.setattr(svc, "GUIDANCE_FILE", write(tmp_path, yaml.safe_dump(bad, allow_unicode=True)))
    svc.load_guidance.cache_clear()
    with pytest.raises(ValueError):
        svc.load_guidance()
    svc.load_guidance.cache_clear()
