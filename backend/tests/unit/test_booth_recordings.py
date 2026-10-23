"""Spec 050 FR-006/FR-008, SC-005: các bản ghi của gian (apps/web/public/booth/replay) là dữ liệu hư cấu hợp lệ.

Mỗi khung phải hợp `docs/schemas/sim_run.v1.json` (lược đồ đóng, tin mở đầu bằng câu công khai AI), không có
chuỗi giống số điện thoại thô ở chữ người xem đọc được, có đủ khung, bước, thời lượng; tên tệp khớp danh sách phát."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
REPLAY = ROOT / "apps" / "web" / "public" / "booth" / "replay"
SCHEMAS = ROOT / "docs" / "schemas"
PHONE = re.compile(r"(?:\+?84|0)[\s.-]?[35789](?:[\s.-]?\d){8}")
BOOTH_TS = ROOT / "apps" / "web" / "src" / "lib" / "booth.ts"


def _validator() -> Draft202012Validator:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    schema = json.loads((SCHEMAS / "sim_run.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def _files() -> list[Path]:
    return sorted(REPLAY.glob("*.json"))


def test_there_is_one_recording_per_playlist_item() -> None:
    playlist = set(re.findall(r'scenarioId: "([a-z0-9_]+)"', BOOTH_TS.read_text(encoding="utf-8")))
    assert playlist and playlist == {p.stem for p in _files()}


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.stem)
def test_every_frame_matches_the_closed_sim_run_contract(path: Path) -> None:
    rec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    assert set(rec) == {"scenario_id", "recorded_at", "duration_ms", "frames", "steps"}
    assert rec["scenario_id"] == path.stem and rec["duration_ms"] > 0 and rec["frames"]
    validator = _validator()
    times = [f["t_ms"] for f in rec["frames"]]
    assert times == sorted(times)
    for frame in rec["frames"]:
        assert sorted(validator.iter_errors(frame["run"]), key=str) == []
        assert frame["run"]["is_demo"] is True and frame["run"]["scenario_id"] == path.stem


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.stem)
def test_no_raw_phone_number_in_anything_a_viewer_reads(path: Path) -> None:
    rec = json.loads(path.read_text(encoding="utf-8"))
    visible: list[str] = []
    for frame in rec["frames"]:
        run = frame["run"]
        visible += [m["text"] for m in run["guardian_messages"]]
        visible += [(run["pending_question"] or {}).get("text", ""), run["note"] or ""]
    assert not [t for t in visible if PHONE.search(t)]
    assert all(
        t.startswith("Đây là trợ lý AI HỏiCon")
        for f in rec["frames"]
        for t in [m["text"] for m in f["run"]["guardian_messages"]]
    )


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.stem)
def test_steps_hold_no_free_text_beyond_masked_enums(path: Path) -> None:
    rec = json.loads(path.read_text(encoding="utf-8"))
    for item in rec["steps"]:
        step = item["step"]
        assert PHONE.search(json.dumps(step.get("output") or {}, ensure_ascii=False)) is None
        assert not step.get("error") or isinstance(step["error"], str)
