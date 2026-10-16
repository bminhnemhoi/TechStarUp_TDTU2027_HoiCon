"""Kịch bản diễn tập và chấm điểm tất định (spec 028, P2-13, plan D4). KHÔNG gọi LLM.

Kịch bản là tệp `data/drills/*.yaml` khớp `docs/schemas/drill_script.v1.json`: nạp một lần, kiểm schema, kiểm thêm hai
điều schema không diễn đạt được (tên tệp = `id`, mỗi bước có đúng 1 lựa chọn đúng). Một tệp hỏng làm cả lần nạp lỗi
(`DrillScriptError`): thà không mở diễn tập còn hơn mở bài sai.

Máy chỉ gửi MÃ lựa chọn (`{"step": 0, "choice_id": "b"}`). Máy chủ chấm lại hoàn toàn từ kịch bản của mình: mọi trường
khác trong câu trả lời (`correct`, `score`, văn bản) bị bỏ qua, không bao giờ lưu.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]
DRILLS_DIR = ROOT / "data" / "drills"
SCHEMA_PATH = ROOT / "docs" / "schemas" / "drill_script.v1.json"


class DrillScriptError(ValueError):
    """Một tệp kịch bản không hợp lệ (schema, tên tệp, số lựa chọn đúng)."""


class InvalidAnswers(ValueError):
    """Câu trả lời không khớp kịch bản: mã lạ, sai thứ tự bước, thiếu/thừa bước. Không nêu giá trị máy gửi."""


@dataclass(frozen=True)
class Grade:
    score: int  # số bước chọn đúng
    total: int

    @property
    def passed(self) -> bool:
        return self.score == self.total


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def load_scripts(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Nạp và kiểm mọi `*.yaml` trong `directory` (mặc định `data/drills`). Trả {id: kịch bản}."""
    loaded: dict[str, dict[str, Any]] = {}
    for path in sorted((directory or DRILLS_DIR).glob("*.yaml")):
        try:
            script = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise DrillScriptError(f"{path.name}: không đọc được ({type(exc).__name__})") from None
        errors = sorted(_validator().iter_errors(script), key=lambda e: list(e.path))
        if errors:
            where = "/".join(map(str, errors[0].path)) or "(gốc)"
            raise DrillScriptError(f"{path.name}: sai schema tại {where}")
        if script["id"] != path.stem:
            raise DrillScriptError(f"{path.name}: id không khớp tên tệp")
        for index, step in enumerate(script["steps"]):
            if sum(1 for c in step["choices"] if c["correct"]) != 1 or len({c["id"] for c in step["choices"]}) != 2:
                raise DrillScriptError(f"{path.name}: bước {index} phải có đúng 1 lựa chọn đúng và 2 mã khác nhau")
        loaded[script["id"]] = script
    return loaded


@lru_cache(maxsize=1)
def _default_scripts() -> dict[str, dict[str, Any]]:
    return load_scripts()


def get_script(script_id: str) -> dict[str, Any] | None:
    return _default_scripts().get(script_id)


def reset_cache() -> None:
    """Cho test: nạp lại `data/drills` ở lần gọi kế tiếp."""
    _default_scripts.cache_clear()


def normalize_answers(
    script: Mapping[str, Any], answers: Sequence[Mapping[str, Any]], *, complete: bool
) -> list[dict[str, Any]]:
    """Kiểm và rút gọn câu trả lời về `[{"step", "choice_id"}]`.

    Phải là bước 0, 1, 2… liên tiếp, đúng thứ tự, mỗi bước một lần, mã thuộc lựa chọn của bước đó. `complete=True` (kết
    quả `completed`) đòi đủ mọi bước; `complete=False` (`aborted`) cho phép dừng giữa chừng nên chỉ cần là một tiền tố.
    """
    steps = script["steps"]
    if len(answers) > len(steps) or (complete and len(answers) != len(steps)):
        raise InvalidAnswers("số câu trả lời không khớp số bước")
    clean: list[dict[str, Any]] = []
    for index, answer in enumerate(answers):
        step, choice_id = answer.get("step"), answer.get("choice_id")
        if type(step) is not int or step != index:
            raise InvalidAnswers("thứ tự bước không đúng")
        if choice_id not in {c["id"] for c in steps[index]["choices"]}:
            raise InvalidAnswers("mã lựa chọn không thuộc bước này")
        clean.append({"step": index, "choice_id": choice_id})
    return clean


def grade(script: Mapping[str, Any], answers: Sequence[Mapping[str, Any]]) -> Grade:
    """Chấm một kết quả `completed`: `passed` khi mọi bước chọn đúng. Câu trả lời sai cấu trúc ⇒ `InvalidAnswers`."""
    clean = normalize_answers(script, answers, complete=True)
    score = 0
    for answer, step in zip(clean, script["steps"], strict=True):
        score += any(c["id"] == answer["choice_id"] and c["correct"] for c in step["choices"])
    return Grade(score=score, total=len(script["steps"]))


def red_flags(script: Mapping[str, Any]) -> list[str]:
    return list(script["debrief"]["red_flags_vi"])
