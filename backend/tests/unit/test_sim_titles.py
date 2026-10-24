"""Spec 033 FR-015: tên kịch bản tiếng Việt dựng tất định từ nhóm thủ đoạn + số thứ tự."""

import json
from pathlib import Path

import pytest

from hoicon.services import sim_service

SCHEMA = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "scenario.v1.json"


def test_every_category_of_the_contract_has_a_label() -> None:
    categories = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]["category"]["enum"]
    assert sorted(sim_service.SCENARIO_TITLE_VI) == sorted(categories)
    assert len(categories) == 18


@pytest.mark.parametrize(
    ("case_id", "category", "expected"),
    [
        ("fake_police_safe_account_002", "fake_police", "Giả danh công an · ca 2"),
        ("prize_gift_001", "prize_gift", "Trúng thưởng, quà tặng · ca 1"),
        ("benign_bank_012", "benign_bank", "Cuộc gọi thật: ngân hàng · ca 12"),
        ("fake_tax_100", "fake_tax", "Giả danh cơ quan thuế · ca 100"),
    ],
)
def test_title_is_label_plus_case_number_without_leading_zeros(case_id: str, category: str, expected: str) -> None:
    assert sim_service.title_vi(case_id, category) == expected


def test_a_category_without_a_label_is_an_error_not_a_blank() -> None:
    with pytest.raises(KeyError):
        sim_service.title_vi("brand_new_001", "brand_new")
