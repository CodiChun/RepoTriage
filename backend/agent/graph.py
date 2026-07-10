from langgraph.graph import END, StateGraph

from agent.nodes import (
    assess_severity_node,
    classify_node,
    decide_route_node,
    draft_reply_node,
    find_code_node,
    find_similar_node,
    route_decision,
)
from agent.state import TriageState


def build_triage_graph():
    graph = StateGraph(TriageState)

    graph.add_node("classify", classify_node)
    graph.add_node("find_similar", find_similar_node)
    graph.add_node("find_code", find_code_node)
    graph.add_node("assess_severity", assess_severity_node)
    graph.add_node("decide_route", decide_route_node)
    graph.add_node("generate_reply", draft_reply_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "find_similar")
    graph.add_edge("find_similar", "find_code")
    graph.add_edge("find_code", "assess_severity")
    graph.add_edge("assess_severity", "decide_route")
    graph.add_conditional_edges(
        "decide_route",
        route_decision,
        {
            "duplicate_path": "generate_reply",
            "bug_analysis_path": "generate_reply",
            "answer_path": "generate_reply",
            "need_more_info_path": "generate_reply",
        },
    )
    graph.add_edge("generate_reply", END)

    return graph.compile()


triage_graph = build_triage_graph()
