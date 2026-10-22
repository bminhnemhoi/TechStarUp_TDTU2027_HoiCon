"""`GET /v1/graphs/incident` (spec 033 FR-009): sơ đồ đồ thị tác tử cho `/trace` và `/sim`. Không cổng, không đăng nhập:
chỉ mô tả cấu trúc mã, không có dữ liệu người dùng."""

from typing import Any, Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel

from hoicon.services.graph_topology import cached_topology

router = APIRouter(prefix="/v1/graphs", tags=["graphs"])


class TopologyNode(BaseModel):
    id: str
    label_vi: str
    kind: Literal["start", "end", "node", "interrupt"]
    step_nodes: list[str]


class TopologyEdge(BaseModel):
    source: str
    target: str
    conditional: bool


class GraphTopologyOut(BaseModel):
    """Khớp `docs/schemas/graph_topology.v1.json`."""

    graph: Literal["incident"]
    version: str
    nodes: list[TopologyNode]
    edges: list[TopologyEdge]


@router.get("/incident", response_model=GraphTopologyOut)
async def get_incident_graph(response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "public, max-age=300"
    return cached_topology()
