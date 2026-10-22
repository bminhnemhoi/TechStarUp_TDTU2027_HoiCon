"""`GET /v1/graphs/incident` (spec 033 FR-009): sơ đồ đồ thị sự cố SINH từ đồ thị đã biên dịch, không chép tay.

Chỉ mô tả cấu trúc mã (không dữ liệu người dùng), nên route không cần đăng nhập. Khớp `graph_topology.v1.json`."""

import hashlib
import json
from functools import lru_cache
from typing import Any

from hoicon.agents import incident_graph
from hoicon.config import get_settings

BOUNDARY_LABELS = {"__start__": ("Bắt đầu", "start"), "__end__": ("Kết thúc", "end")}


class MissingLabelError(Exception):
    """Đồ thị có nút chưa có nhãn tiếng Việt trong `NODE_LABELS_VI`."""


def _compile() -> Any:
    deps = incident_graph.Deps(router=None, sessions=None, settings=get_settings())  # type: ignore[arg-type]
    return incident_graph.build_graph(deps).compile().get_graph()


def graph_topology() -> dict[str, Any]:
    graph = _compile()
    nodes: list[dict[str, Any]] = []
    for node_id in graph.nodes:
        if node_id in BOUNDARY_LABELS:
            label, kind = BOUNDARY_LABELS[node_id]
            nodes.append({"id": node_id, "label_vi": label, "kind": kind, "step_nodes": []})
            continue
        label = incident_graph.NODE_LABELS_VI.get(node_id)
        if label is None:
            raise MissingLabelError(node_id)
        kind = "interrupt" if node_id in incident_graph.INTERRUPT_NODES else "node"
        nodes.append(
            {
                "id": node_id,
                "label_vi": label,
                "kind": kind,
                "step_nodes": incident_graph.STEP_NODES.get(node_id, [node_id]),
            }
        )
    edges = [{"source": e.source, "target": e.target, "conditional": bool(e.conditional)} for e in graph.edges]
    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["source"], e["target"]))
    digest = hashlib.sha256(
        json.dumps([[n["id"] for n in nodes], [[e["source"], e["target"]] for e in edges]]).encode()
    ).hexdigest()
    return {"graph": "incident", "version": digest[:12], "nodes": nodes, "edges": edges}


@lru_cache(maxsize=1)
def cached_topology() -> dict[str, Any]:
    return graph_topology()
