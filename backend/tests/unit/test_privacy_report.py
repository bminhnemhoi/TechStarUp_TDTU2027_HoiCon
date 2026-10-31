"""Spec 037 FR-006 / SC-004: báo cáo quyền riêng tư sinh từ model, bắt bảng mới quên ánh xạ, bắt số điện thoại thô."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, Table

from hoicon.db.models import Base
from hoicon.ops import privacy_report as pr
from hoicon.services.retention_service import RETENTION


def test_every_table_of_the_model_has_a_row_and_nothing_is_stale() -> None:
    rows, problems = pr.inventory()
    assert problems == []
    assert {r["table"] for r in rows} == set(Base.metadata.tables)
    assert all(r["purpose"] and r["retention"] and r["personal"] for r in rows)


def test_a_new_table_without_a_mapping_makes_the_report_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    ghost = Table("ghost_table_for_test", MetaData(), Column("id", Integer, primary_key=True))
    tables = {**Base.metadata.tables, "ghost_table_for_test": ghost}  # `metadata.tables` bất biến: thay cả `Base`
    monkeypatch.setattr(pr, "Base", SimpleNamespace(metadata=SimpleNamespace(tables=tables)))
    _, problems = pr.inventory()
    assert problems == ["ghost_table_for_test: bảng chưa có trong DATA_MAP"]
    report = {"table_problems": problems, "raw_phone_hits": [], "fixture_phone_hits": [], "consent_text_problems": []}
    report["pii_rows"] = None
    assert pr.exit_code(report) == 1


def test_a_mapping_for_a_dropped_table_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(pr.DATA_MAP, "dropped_table", ("x", "y", "z"))
    assert "dropped_table: có trong DATA_MAP nhưng không còn trong model" in pr.inventory()[1]


def test_retention_days_come_from_the_single_source_not_a_copy() -> None:
    by_table = {r["table"]: r["retention"] for r in pr.inventory()[0]}
    assert by_table["risk_events"] == f"{RETENTION['risk_events'].days} ngày"
    assert by_table["jobs"] == f"{RETENTION['jobs'].days} ngày"
    assert by_table["consents"].startswith("không xóa")


def test_the_phone_scan_flags_real_looking_numbers_but_not_fictional_ones_or_url_digits(tmp_path: Path) -> None:
    src = tmp_path / "backend" / "src"
    src.mkdir(parents=True)
    (src / "ok.py").write_text(
        'FAKE = "0900000123"\nURL = "https://x.vn/a-185260813120338251.htm"\nid = "01a1663f-ba3f"\n'
    )
    (src / "bad.py").write_text('number = "0912' + '345678"\n')
    hits = pr.scan_phones(("backend/src",), tmp_path)
    assert hits == ["backend/src/bad.py:1"]
    assert not any("0912" in h for h in hits)  # đường dẫn:dòng, không bao giờ in số


def test_a_missing_source_root_is_reported_not_silently_clean(tmp_path: Path) -> None:
    assert pr.scan_phones(("apps/web/src",), tmp_path) == ["apps/web/src: không tìm thấy thư mục, chưa quét được"]


def test_the_phone_scan_catches_numbers_written_with_spaces_or_dots(tmp_path: Path) -> None:
    src = tmp_path / "backend" / "src"
    src.mkdir(parents=True)
    (src / "a.py").write_text('x = "' + "0912" + " 345" + " 678" + '"\n')
    (src / "b.py").write_text('y = "' + "0987" + ".654" + ".321" + '"\n')
    assert pr.scan_phones(("backend/src",), tmp_path) == ["backend/src/a.py:1", "backend/src/b.py:1"]


def test_the_real_source_tree_has_no_raw_phone_numbers() -> None:
    assert pr.scan_phones() == []


def test_the_consent_texts_match_the_code() -> None:
    from hoicon.ops import consent_texts

    assert consent_texts.problems() == []


def test_the_report_text_never_prints_a_number_or_row_content() -> None:
    rows, _ = pr.inventory()
    text = pr.render(
        {
            "tables": rows,
            "table_problems": [],
            "raw_phone_hits": ["a.py:3"],
            "fixture_phone_hits": [],
            "consent_text_problems": [],
            "pii_rows": {"jobs.payload": 2},
        }
    )
    assert "a.py:3" in text and '"jobs.payload": 2' in text
    assert not pr.PHONE.search(text)


def test_the_repository_fixtures_are_clean_apart_from_the_deliberate_negative_one() -> None:
    hits = [h for h in pr.scan_phones(pr.FIXTURE_ROOTS) if h.split(":")[0] not in pr.NEGATIVE_FIXTURES]
    assert hits == []


def test_a_fixture_hit_makes_the_report_fail() -> None:
    report = {
        "table_problems": [],
        "raw_phone_hits": [],
        "fixture_phone_hits": ["data/x.json:1"],
        "consent_text_problems": [],
        "pii_rows": None,
    }
    assert pr.exit_code(report) == 1
