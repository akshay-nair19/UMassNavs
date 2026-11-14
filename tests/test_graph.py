from dataclasses import replace

import pytest

from app.graph import load_graph, strict_step_free_edges, validate_graph


def test_map_only_graph_cannot_supply_a_step_free_route():
    graph = load_graph()
    assert validate_graph(graph) == []
    assert strict_step_free_edges(graph) == ()


def test_candidate_cannot_be_promoted_without_field_evidence():
    graph = load_graph()
    promoted = replace(graph, edges=(replace(graph.edges[0], status="production", step_free_status="verified"),))
    errors = validate_graph(promoted)
    assert any("field-verified" in error for error in errors)
    assert any("unverified entrance" in error for error in errors)
    with pytest.raises(ValueError, match="Invalid campus graph"):
        strict_step_free_edges(promoted)


def test_missing_source_reference_fails_validation():
    graph = load_graph()
    broken = replace(graph, edges=(replace(graph.edges[0], evidence_ids=("missing-evidence",)),))
    assert any("existing evidence IDs" in error for error in validate_graph(broken))
