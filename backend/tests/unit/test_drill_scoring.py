"""Chấm điểm diễn tập tất định (spec 028 FR-004, plan D4): máy chủ chấm lại độc lập, chỉ từ mã lựa chọn."""

from pathlib import Path

import pytest
import yaml

from hoicon.domain import drill as dr

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def scripts() -> dict[str, dict]:
    return dr.load_scripts()


@pytest.fixture
def script(scripts: dict[str, dict]) -> dict:
    return scripts["drill_bank_card_locked"]


def right(script: dict) -> list[dict]:
    return [
        {"step": i, "choice_id": next(c["id"] for c in step["choices"] if c["correct"])}
        for i, step in enumerate(script["steps"])
    ]


def wrong(script: dict, step: int) -> dict:
    return {"step": step, "choice_id": next(c["id"] for c in script["steps"][step]["choices"] if not c["correct"])}


def test_the_three_shipped_scripts_load_and_validate(scripts: dict[str, dict]) -> None:
    assert set(scripts) == {"drill_police_safe_account", "drill_bank_card_locked", "drill_relative_urgent_money"}
    assert dr.get_script("drill_bank_card_locked") == scripts["drill_bank_card_locked"]
    assert dr.get_script("drill_nope") is None


def test_every_right_answer_passes_every_script(scripts: dict[str, dict]) -> None:
    for script in scripts.values():
        grade = dr.grade(script, right(script))
        assert grade.passed and grade.score == grade.total == len(script["steps"])


def test_one_wrong_answer_fails_with_the_right_count(script: dict) -> None:
    for bad_step in range(len(script["steps"])):
        answers = right(script)
        answers[bad_step] = wrong(script, bad_step)
        grade = dr.grade(script, answers)
        assert not grade.passed
        assert grade.score == len(script["steps"]) - 1


def test_all_wrong_scores_zero(script: dict) -> None:
    grade = dr.grade(script, [wrong(script, i) for i in range(len(script["steps"]))])
    assert not grade.passed and grade.score == 0


def test_an_unknown_choice_code_is_an_error_not_a_wrong_answer(script: dict) -> None:
    answers = right(script)
    answers[1] = {"step": 1, "choice_id": "z"}
    with pytest.raises(dr.InvalidAnswers):
        dr.grade(script, answers)


def test_steps_out_of_order_are_an_error(script: dict) -> None:
    answers = right(script)
    answers[0], answers[1] = answers[1], answers[0]
    with pytest.raises(dr.InvalidAnswers):
        dr.grade(script, answers)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda a: a[:-1],  # thiếu bước cuối
        lambda a: [a[0], a[2]],  # nhảy cóc
        lambda a: [*a, a[-1]],  # thừa bước
        lambda a: [a[0], a[0], a[2]],  # lặp bước
        lambda a: [],  # hoàn tất mà không có câu trả lời
        lambda a: [{"step": -1, "choice_id": "a"}, *a[1:]],
    ],
    ids=["missing", "gap", "extra", "repeat", "empty", "negative"],
)
def test_a_completed_result_must_answer_every_step_exactly_once_in_order(script: dict, mutate) -> None:
    with pytest.raises(dr.InvalidAnswers):
        dr.grade(script, mutate(right(script)))


def test_the_server_regrades_and_ignores_extra_claims_in_the_answers(script: dict) -> None:
    """Máy có thể nhét `correct`/`score` vào từng câu trả lời; chấm điểm chỉ nhìn `step` + `choice_id`."""
    answers = [{**wrong(script, i), "correct": True, "score": 99} for i in range(len(script["steps"]))]
    grade = dr.grade(script, answers)
    assert not grade.passed and grade.score == 0


def test_a_partial_prefix_is_valid_for_an_aborted_drill(script: dict) -> None:
    prefix = right(script)[:1]
    assert dr.normalize_answers(script, prefix, complete=False) == prefix
    assert dr.normalize_answers(script, [], complete=False) == []
    assert dr.normalize_answers(script, right(script), complete=False) == right(script)


@pytest.mark.parametrize(
    "answers",
    [
        [{"step": 1, "choice_id": "a"}],  # không bắt đầu từ bước 0
        [{"step": 0, "choice_id": "a"}, {"step": 2, "choice_id": "a"}],
        [{"step": 0, "choice_id": "q"}],
    ],
    ids=["not-from-zero", "gap", "unknown-code"],
)
def test_a_partial_result_must_still_be_a_valid_prefix(script: dict, answers: list[dict]) -> None:
    with pytest.raises(dr.InvalidAnswers):
        dr.normalize_answers(script, answers, complete=False)


def test_more_answers_than_steps_is_an_error_even_when_partial(script: dict) -> None:
    too_many = [*right(script), {"step": len(script["steps"]), "choice_id": "a"}]
    with pytest.raises(dr.InvalidAnswers):
        dr.normalize_answers(script, too_many, complete=False)


def test_normalized_answers_carry_only_the_two_fields(script: dict) -> None:
    noisy = [{**a, "note": "bác thấy lạ"} for a in right(script)]
    assert dr.normalize_answers(script, noisy, complete=True) == right(script)


def test_debrief_red_flags_come_from_the_script(script: dict) -> None:
    assert dr.red_flags(script) == script["debrief"]["red_flags_vi"]


def _write(dir_: Path, name: str, doc: dict) -> None:
    (dir_ / f"{name}.yaml").write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")


def test_a_file_that_breaks_the_schema_stops_the_load(tmp_path: Path, script: dict) -> None:
    broken = {**script, "id": "drill_broken_one"}
    del broken["approved"]
    _write(tmp_path, "drill_broken_one", broken)
    with pytest.raises(dr.DrillScriptError):
        dr.load_scripts(tmp_path)


def test_a_file_whose_name_differs_from_its_id_stops_the_load(tmp_path: Path, script: dict) -> None:
    _write(tmp_path, "something_else", script)
    with pytest.raises(dr.DrillScriptError):
        dr.load_scripts(tmp_path)


def test_a_step_without_exactly_one_right_choice_stops_the_load(tmp_path: Path, script: dict) -> None:
    two_right = yaml.safe_load(yaml.safe_dump(script))
    two_right["id"] = "drill_two_right"
    for choice in two_right["steps"][0]["choices"]:
        choice["correct"] = True
    _write(tmp_path, "drill_two_right", two_right)
    with pytest.raises(dr.DrillScriptError):
        dr.load_scripts(tmp_path)
