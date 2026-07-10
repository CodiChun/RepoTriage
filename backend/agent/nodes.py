from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from agent.state import TriageState
from agent.tools import (
    get_code_vectorstore,
    get_issue_vectorstore,
    is_likely_duplicate,
    similarity_search_with_score,
)
from config import LLM_MODEL, LLM_PROVIDER


def get_llm():
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(model=LLM_MODEL, temperature=0)
    return ChatAnthropic(model=LLM_MODEL, temperature=0)


def classify_node(state: TriageState) -> TriageState:
    llm = get_llm()
    prompt = f"""Analyze the following GitHub issue and classify it as exactly one of:
bug, feature_request, question, unclear

Title: {state['issue_title']}
Body: {state['issue_body'] or '(empty)'}

Return only the classification word, nothing else."""
    result = llm.invoke(prompt)
    category = result.content.strip().lower().replace(" ", "_")
    state["category"] = category
    state["reasoning_log"].append(f"Classified as: {category}")
    return state


def find_similar_node(state: TriageState) -> TriageState:
    vectorstore = get_issue_vectorstore()
    if not vectorstore:
        state["similar_issues"] = []
        state["reasoning_log"].append("No issue vectorstore available; skipped similarity search")
        return state

    query = f"{state['issue_title']} {state['issue_body'] or ''}"
    results = similarity_search_with_score(vectorstore, query, k=3)

    similar = []
    for r in results:
        meta = r["metadata"]
        if meta.get("number") == state["issue_number"]:
            continue
        similar.append(
            {
                "number": meta.get("number"),
                "title": meta.get("title"),
                "score": r["score"],
            }
        )

    state["similar_issues"] = similar[:3]
    if similar:
        state["reasoning_log"].append(
            f"Found {len(similar)} similar issues; top match #{similar[0]['number']} (score={similar[0]['score']})"
        )
    else:
        state["reasoning_log"].append("No similar issues found")
    return state


def find_code_node(state: TriageState) -> TriageState:
    vectorstore = get_code_vectorstore()
    if not vectorstore:
        state["relevant_code_files"] = []
        state["reasoning_log"].append("No code vectorstore available; skipped code search")
        return state

    query = f"{state['issue_title']} {state['issue_body'] or ''}"
    results = similarity_search_with_score(vectorstore, query, k=3)

    state["relevant_code_files"] = [
        {
            "file": r["metadata"].get("source", r["metadata"].get("file_path", "unknown")),
            "snippet": r["content"],
            "score": r["score"],
        }
        for r in results
    ]
    state["reasoning_log"].append(f"Found {len(state['relevant_code_files'])} relevant code files")
    return state


def assess_severity_node(state: TriageState) -> TriageState:
    if state["category"] != "bug":
        state["severity"] = None
        return state

    llm = get_llm()
    prompt = f"""Assess the severity of this bug report as: high, medium, or low.

Title: {state['issue_title']}
Body: {state['issue_body'] or '(empty)'}
Relevant code: {state['relevant_code_files']}

Return only the severity word."""
    result = llm.invoke(prompt)
    severity = result.content.strip().lower()
    state["severity"] = severity
    state["reasoning_log"].append(f"Bug severity assessed as: {severity}")
    return state


def decide_route_node(state: TriageState) -> TriageState:
    if is_likely_duplicate(state.get("similar_issues", [])):
        state["route_taken"] = "duplicate_path"
        state["reasoning_log"].append("Routing: duplicate_path (high similarity to existing issue)")
        return state

    category = state.get("category", "unclear")
    if category == "bug" and state.get("relevant_code_files"):
        state["route_taken"] = "bug_analysis_path"
        state["reasoning_log"].append("Routing: bug_analysis_path (bug with relevant code context)")
        return state

    if category == "question":
        state["route_taken"] = "answer_path"
        state["reasoning_log"].append("Routing: answer_path (question category)")
        return state

    state["route_taken"] = "need_more_info_path"
    state["reasoning_log"].append("Routing: need_more_info_path (insufficient context)")
    return state


def route_decision(state: TriageState) -> str:
    return state.get("route_taken", "need_more_info_path")


def draft_reply_node(state: TriageState) -> TriageState:
    llm = get_llm()
    route = state.get("route_taken", "need_more_info_path")

    route_instructions = {
        "duplicate_path": "Politely inform the reporter this may be a duplicate and link to the similar issue.",
        "bug_analysis_path": "Acknowledge the bug, summarize relevant code context, and suggest next debugging steps.",
        "answer_path": "Provide a helpful, concise answer based on available context.",
        "need_more_info_path": "Ask clarifying questions to gather more information before proceeding.",
    }

    context = f"""
Category: {state['category']}
Severity: {state.get('severity', 'N/A')}
Route: {route}
Similar issues: {state['similar_issues']}
Relevant code: {state['relevant_code_files']}
"""
    prompt = f"""You are a friendly, professional open-source maintainer.
Based on the context below, draft a GitHub issue reply in English.

Instructions: {route_instructions.get(route, route_instructions['need_more_info_path'])}

Context:
{context}

Original issue:
Title: {state['issue_title']}
Body: {state['issue_body'] or '(empty)'}
"""
    result = llm.invoke(prompt)
    state["draft_reply"] = result.content
    state["needs_human_review"] = True
    state["reasoning_log"].append("Generated draft reply for human review")
    return state
