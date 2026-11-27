from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.orchestration.driver import drive_graph_until_idle


class RecoveryState(TypedDict):
    current_stage: str


@pytest.mark.asyncio
async def test_historical_recovery_advances_after_each_approval():
    calls = []

    def outline_approval(state):
        interrupt({"gate": "outline"})
        return {"current_stage": "outline_approval"}

    def characters(state):
        calls.append("characters")
        return {"current_stage": "plan_characters"}

    def characters_approval(state):
        interrupt({"gate": "plan"})
        return {"current_stage": "characters_approval"}

    def shots(state):
        calls.append("shots")
        return {"current_stage": "plan_shots"}

    graph = StateGraph(RecoveryState)
    for name, node in [
        ("outline_approval", outline_approval),
        ("characters", characters),
        ("characters_approval", characters_approval),
        ("shots", shots),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "outline_approval")
    graph.add_edge("outline_approval", "characters")
    graph.add_edge("characters", "characters_approval")
    graph.add_edge("characters_approval", "shots")
    graph.add_edge("shots", END)
    compiled = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "historical-recovery"}}
    await compiled.ainvoke({"current_stage": "plan_outline"}, config)
    snapshot = await compiled.aget_state(config)
    historical_id = snapshot.config["configurable"]["checkpoint_id"]
    approvals = []

    async def approve(item):
        approvals.append(item.value["gate"])
        assert len(approvals) <= 2, "Recovery rewound an already approved stage"
        return {"action": "approve", "feedback": ""}

    result = await drive_graph_until_idle(
        compiled,
        initial_payload=None,
        graph_config=snapshot.config,
        runtime_context=None,
        on_interrupt=approve,
    )
    assert approvals == ["outline", "plan"]
    assert calls == ["characters", "shots"]
    assert result.final_stage == "plan_shots"
    assert snapshot.config["configurable"]["checkpoint_id"] == historical_id
