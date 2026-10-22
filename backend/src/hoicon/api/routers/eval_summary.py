"""`GET /v1/eval/summary` (spec 033 FR-012, P3): các baseline eval ĐÃ COMMIT cho trang `/eval` của BGK.

Cùng cổng và cùng phiên người giám hộ DEMO với `/v1/sim/*`. Chỉ đọc `backend/eval/baseline*.json`, KHÔNG đọc `reports/`
(bị git bỏ qua, có thể chứa `run_id`). Baseline không có dữ liệu người dùng. Số trên cassette `synthetic` hoặc kịch bản
`draft` chỉ là "số rào tất định", CHƯA PHẢI SỐ M3: trường `gate` nói thẳng điều đó.
"""

import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from hoicon.api.auth import GuardianClaims
from hoicon.api.routers import sim
from hoicon.eval import cases

router = APIRouter(prefix="/v1/eval", tags=["eval"], dependencies=[Depends(sim.require_sim_enabled)])
Guardian = Annotated[GuardianClaims, Depends(sim.demo_guardian)]


class EvalGate(BaseModel):
    verdict: Literal["provisional", "recorded"]
    reasons: list[str]


class EvalBaseline(BaseModel):
    suite: str
    created: str
    git_sha: str
    cassette_source: str
    provisional_cases: int | None
    metrics: dict[str, float | int]


class EvalSuite(BaseModel):
    suite: str
    baseline: EvalBaseline
    gate: EvalGate


class EvalSummary(BaseModel):
    suites: list[EvalSuite]


def _gate(doc: dict[str, Any]) -> EvalGate:
    reasons = []
    if doc.get("cassette_source") != "recorded":
        reasons.append("Cassette `synthetic`: chỉ đo các rào tất định, chưa đo model thật")
    if (doc.get("provisional_cases") or 0) > 0:
        reasons.append("Kịch bản còn ở trạng thái nháp (chưa được duyệt)")
    return EvalGate(verdict="provisional" if reasons else "recorded", reasons=reasons)


def load_summary() -> EvalSummary:
    suites = []
    for path in sorted(cases.EVAL_DIR.glob("baseline*.json")):  # không bao giờ đụng `reports/` hay `cassettes/`
        doc = json.loads(path.read_text(encoding="utf-8"))
        suites.append(
            EvalSuite(
                suite=doc["suite"],
                baseline=EvalBaseline(
                    suite=doc["suite"],
                    created=doc["created"],
                    git_sha=doc["git_sha"],
                    cassette_source=doc["cassette_source"],
                    provisional_cases=doc.get("provisional_cases"),
                    metrics={k: v for k, v in doc["metrics"].items() if isinstance(v, int | float)},
                ),
                gate=_gate(doc),
            )
        )
    return EvalSummary(suites=suites)


@router.get("/summary", response_model=EvalSummary)
async def get_summary(_: Guardian) -> EvalSummary:
    return load_summary()
