"""Spec 033 FR-009: `GET /v1/graphs/incident` sinh từ đồ thị đã biên dịch, khớp `graph_topology.v1.json`."""

import json
from pathlib import Path

import pytest
from consent_support import call
from jsonschema import Draft202012Validator

from hoicon.agents import incident_graph
from hoicon.services import graph_topology

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "schemas" / "graph_topology.v1.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA)


async def test_route_is_public_valid_and_cacheable() -> None:
    res = await call("GET", "/v1/graphs/incident")
    assert res.status_code == 200, res.text
    VALIDATOR.validate(res.json())
    assert "max-age" in res.headers["cache-control"]


def test_nodes_are_exactly_the_compiled_graph_nodes_with_labels() -> None:
    topology = graph_topology.graph_topology()
    compiled = graph_topology._compile()
    assert {n["id"] for n in topology["nodes"]} == set(compiled.nodes)
    real = {n["id"] for n in topology["nodes"]} - {"__start__", "__end__"}
    assert real == set(incident_graph.NODE_LABELS_VI)
    assert {n["id"] for n in topology["nodes"] if n["kind"] == "interrupt"} == {
        "ask_elder",
        "await_guardian",
        "await_case_approval",
    }
    assert next(n for n in topology["nodes"] if n["id"] == "verification")["step_nodes"] == ["verify"]


def test_a_node_without_a_label_makes_the_topology_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    original = incident_graph.build_graph

    def with_extra_node(deps: incident_graph.Deps):
        graph = original(deps)
        graph.add_node("brand_new_node", lambda state: {})
        graph.add_edge("ingest", "brand_new_node")
        graph.add_edge("brand_new_node", "risk_scorer")
        return graph

    monkeypatch.setattr(incident_graph, "build_graph", with_extra_node)
    with pytest.raises(graph_topology.MissingLabelError, match="brand_new_node"):
        graph_topology.graph_topology()


def test_version_changes_when_an_edge_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    before = graph_topology.graph_topology()["version"]
    assert graph_topology.graph_topology()["version"] == before  # tất định
    original = incident_graph.build_graph

    def with_extra_edge(deps: incident_graph.Deps):
        graph = original(deps)
        graph.add_edge("resolve", "ingest")
        return graph

    monkeypatch.setattr(incident_graph, "build_graph", with_extra_edge)
    assert graph_topology.graph_topology()["version"] != before


def test_every_step_node_name_is_a_real_agent_step_name() -> None:
    source = (Path(incident_graph.__file__)).read_text(encoding="utf-8")
    for node in graph_topology.graph_topology()["nodes"]:
        for step in node["step_nodes"]:
            assert f'"{step}"' in source, step
