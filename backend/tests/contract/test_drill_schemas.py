"""Hợp đồng spec 028: `drill_script.v1.json`, `drill_offer.v1.json`, `drill_result.v1.json` và 3 kịch bản
`data/drills/*.yaml`. Nội dung diễn tập phải 100% hư cấu (luật 8): không số điện thoại, không tên cơ quan hay ngân hàng
thật, giọng không gây hoảng sợ (PANIC_PHRASES), đúng 1 lựa chọn đúng mỗi bước."""

import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from hoicon.eval.checks import PANIC_PHRASES, REFUND_PHRASES

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"
DRILLS = sorted((ROOT / "data" / "drills").glob("*.yaml"))
PHONE = re.compile(r"(?<![\d])(?:\+?84|0)[\s.-]?[35789](?:[\s.-]?\d){8}(?!\d)")
# Cơ quan nhà nước thật mà bài diễn tập không được dùng làm tên "người gọi" (cộng thêm danh sách ngân hàng).
REAL_AGENCIES = (
    "bộ công an",
    "bộ tài chính",
    "viện kiểm sát",
    "vksnd",
    "tòa án nhân dân",
    "cục an ninh mạng",
    "cục cảnh sát",
    "cơ quan an ninh điều tra",
    "bảo hiểm xã hội việt nam",
    "tổng cục thuế",
    "ngân hàng nhà nước",
    "evn",
    "vneid",
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMAS.glob("*.json"):
        doc = _load(path)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / f"{name}.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


def _fixtures(name: str, kind: str) -> list[dict]:
    return _load(SCHEMAS / "fixtures" / f"{name}.v1.{kind}.json")


NAMES = ["drill_script", "drill_offer", "drill_result"]
VALIDATORS = {n: _validator(n) for n in NAMES}


def _strings(node):
    """Mọi chuỗi (giá trị) trong một kịch bản, kèm đường dẫn để báo lỗi."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def _bank_names() -> set[str]:
    """Tên app + tên tổ chức (cả phần trong ngoặc) trong `bank_apps.vn.json`, trừ HỏiCon và app demo."""
    apps = _load(ROOT / "data" / "bank_apps.vn.json")["apps"]
    names: set[str] = set()
    for app in apps:
        if "hỏicon" in (app["org"] + app["name"]).lower():
            continue
        names.add(app["name"].lower())
        org = app["org"].lower()
        names.add(re.sub(r"\s*\(.*?\)", "", org).strip())
        names.update(m.lower() for m in re.findall(r"\(([^)]+)\)", app["org"]))
    return {n for n in names if len(n) >= 3}


@pytest.fixture(scope="module")
def drills() -> dict[str, dict]:
    loaded = {path.stem: yaml.safe_load(path.read_text(encoding="utf-8")) for path in DRILLS}
    assert len(loaded) == 3, "spec 028 FR-010: đúng 3 kịch bản diễn tập v1"
    return loaded


@pytest.mark.parametrize("name", NAMES)
def test_valid_fixtures_pass(name: str) -> None:
    docs = _fixtures(name, "valid")
    assert docs, "mỗi schema phải có ít nhất một fixture hợp lệ"
    for doc in docs:
        assert [e.message for e in VALIDATORS[name].iter_errors(_strip(doc))] == [], doc["_name"]


@pytest.mark.parametrize("name", NAMES)
def test_invalid_fixtures_fail(name: str) -> None:
    docs = _fixtures(name, "invalid")
    assert len(docs) >= 5
    for doc in docs:
        assert not VALIDATORS[name].is_valid(_strip(doc)), doc["_why"]


def test_required_invalid_cases_are_present() -> None:
    """Các ca mà T001 bắt buộc có trong fixture invalid."""
    whys = {name: " | ".join(d["_why"] for d in _fixtures(name, "invalid")) for name in NAMES}
    assert "3 lựa chọn" in whys["drill_script"] and "'x1'" in whys["drill_script"]
    assert "is_drill=false" in whys["drill_offer"]
    assert "note" in whys["drill_result"]


def test_result_status_cannot_claim_passed_or_failed() -> None:
    """Máy chỉ báo completed/aborted/declined; máy chủ mới quyết passed/failed (D4)."""
    base = _strip(_fixtures("drill_result", "valid")[0])
    for status in ("passed", "failed", "expired"):
        assert not VALIDATORS["drill_result"].is_valid({**base, "status": status})


def test_every_drill_file_matches_the_schema_and_its_name(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        errors = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in VALIDATORS["drill_script"].iter_errors(drill)]
        assert errors == [], (stem, errors)
        assert drill["id"] == stem


def test_scenario_ref_points_at_a_real_eval_scenario(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        assert (ROOT / "data" / "scenarios" / f"{drill['scenario_ref']}.yaml").exists(), stem


def test_drills_ship_unapproved_until_minh_approves(drills: dict[str, dict]) -> None:
    """FR-010: `approved: false` cho tới khi Minh duyệt (P1-07); bản prod từ chối bài chưa duyệt."""
    assert all(d["approved"] is False for d in drills.values())


def test_each_step_has_exactly_one_correct_choice(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        for index, step in enumerate(drill["steps"]):
            assert sum(c["correct"] for c in step["choices"]) == 1, (stem, index)
            assert len({c["id"] for c in step["choices"]}) == 2, (stem, index)


def test_the_right_answer_is_not_always_in_the_same_slot(drills: dict[str, dict]) -> None:
    """Nếu lựa chọn đúng luôn là "a" thì người tập chỉ cần đoán, không học được gì."""
    for stem, drill in drills.items():
        slots = {next(c["id"] for c in step["choices"] if c["correct"]) for step in drill["steps"]}
        assert len(slots) == 2, stem


def test_no_phone_number_or_long_digit_run_anywhere(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        for text in _strings({k: v for k, v in drill.items() if k != "caller_last3_fictional"}):
            assert not PHONE.search(text), (stem, text)
            assert not re.search(r"\d{4,}", text), (stem, text)
            assert sum(ch.isdigit() for ch in text) <= 3, (stem, text)


def test_only_the_last_three_digits_of_a_fictional_caller_may_appear(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        assert re.fullmatch(r"[0-9]{3}", drill["caller_last3_fictional"]), stem


def test_no_real_agency_or_bank_names(drills: dict[str, dict]) -> None:
    banks = _bank_names()
    assert len(banks) > 20, "danh sách ngân hàng đọc được từ bank_apps.vn.json"
    for stem, drill in drills.items():
        for text in _strings(drill):
            folded = text.lower()
            for name in (*REAL_AGENCIES, *banks):
                # Từ đứng riêng (ranh giới chữ): "mb" không bị bắt trong một từ khác.
                assert not re.search(rf"(?<!\w){re.escape(name)}(?!\w)", folded), (stem, name, text)


def test_tone_is_warm_not_frightening(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        for text in _strings(drill):
            folded = text.lower()
            assert not any(p in folded for p in PANIC_PHRASES), (stem, text)
            assert not any(p in folded for p in REFUND_PHRASES), (stem, text)


def test_debrief_names_at_least_one_red_flag_and_praises(drills: dict[str, dict]) -> None:
    for stem, drill in drills.items():
        assert drill["debrief"]["red_flags_vi"], stem
        assert drill["debrief"]["praise_vi"], stem
