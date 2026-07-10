"""Run evaluation against sample issues and compare agent vs zero-shot baseline."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.graph import triage_graph
from agent.nodes import get_llm
from config import DATA_DIR

LABEL_TO_CATEGORY = {
    "bug": "bug",
    "enhancement": "feature_request",
    "feature": "feature_request",
    "feature request": "feature_request",
    "question": "question",
    "help wanted": "question",
    "duplicate": "duplicate",
}


def derive_actual_label(labels: list[str]) -> str | None:
    for label in labels:
        normalized = label.lower().strip()
        if normalized in LABEL_TO_CATEGORY:
            return LABEL_TO_CATEGORY[normalized]
        for key, category in LABEL_TO_CATEGORY.items():
            if key in normalized:
                return category
    return None


def zero_shot_classify(title: str, body: str) -> str:
    llm = get_llm()
    prompt = f"""Classify this GitHub issue as exactly one of: bug, feature_request, question, unclear

Title: {title}
Body: {body or '(empty)'}

Return only the classification word."""
    result = llm.invoke(prompt)
    return result.content.strip().lower().replace(" ", "_")


def run_agent_eval(issues: list[dict], limit: int | None = None) -> list[dict]:
    results = []
    subset = issues[:limit] if limit else issues

    for i, issue in enumerate(subset):
        print(f"  Agent eval [{i + 1}/{len(subset)}] issue #{issue['number']}...")
        output = triage_graph.invoke(
            {
                "issue_number": issue["number"],
                "issue_title": issue["title"],
                "issue_body": issue.get("body") or "",
                "category": None,
                "similar_issues": [],
                "relevant_code_files": [],
                "severity": None,
                "draft_reply": None,
                "needs_human_review": False,
                "reasoning_log": [],
                "route_taken": None,
            }
        )
        actual = derive_actual_label(issue.get("labels", []))
        predicted = output.get("category")
        results.append(
            {
                "number": issue["number"],
                "predicted": predicted,
                "actual": actual,
                "correct": predicted == actual if actual else None,
                "route_taken": output.get("route_taken"),
            }
        )
    return results


def run_baseline_eval(issues: list[dict], limit: int | None = None) -> list[dict]:
    results = []
    subset = issues[:limit] if limit else issues

    for i, issue in enumerate(subset):
        print(f"  Baseline eval [{i + 1}/{len(subset)}] issue #{issue['number']}...")
        actual = derive_actual_label(issue.get("labels", []))
        predicted = zero_shot_classify(issue["title"], issue.get("body") or "")
        results.append(
            {
                "number": issue["number"],
                "predicted": predicted,
                "actual": actual,
                "correct": predicted == actual if actual else None,
            }
        )
    return results


def compute_accuracy(results: list[dict]) -> float:
    scored = [r for r in results if r["correct"] is not None]
    if not scored:
        return 0.0
    return sum(1 for r in scored if r["correct"]) / len(scored)


def compute_duplicate_accuracy(agent_results: list[dict], issues: list[dict]) -> float:
    """Check if agent routes duplicate-labeled issues to duplicate_path."""
    issue_map = {i["number"]: i for i in issues}
    duplicate_issues = [
        r
        for r in agent_results
        if issue_map.get(r["number"], {}).get("closed_reason") == "duplicate"
        or "duplicate" in [label.lower() for label in issue_map.get(r["number"], {}).get("labels", [])]
    ]
    if not duplicate_issues:
        return 0.0
    correct = sum(1 for r in duplicate_issues if r.get("route_taken") == "duplicate_path")
    return correct / len(duplicate_issues)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RepoTriage evaluation")
    parser.add_argument("--limit", type=int, default=20, help="Number of issues to evaluate")
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    sample_path = DATA_DIR / "sample_issues.json"
    if not sample_path.exists():
        print(f"Error: {sample_path} not found. Run ingestion first.")
        sys.exit(1)

    with open(sample_path) as f:
        issues = json.load(f)

    print(f"\nEvaluating {min(args.limit, len(issues))} issues...\n")

    print("Running agent pipeline...")
    agent_results = run_agent_eval(issues, args.limit)
    agent_accuracy = compute_accuracy(agent_results)
    duplicate_accuracy = compute_duplicate_accuracy(agent_results, issues)

    print("\nRunning zero-shot baseline...")
    baseline_results = run_baseline_eval(issues, args.limit)
    baseline_accuracy = compute_accuracy(baseline_results)

    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)
    print(f"{'Method':<30} {'Classification Accuracy':>20}")
    print("-" * 50)
    print(f"{'Zero-shot LLM baseline':<30} {baseline_accuracy:>19.1%}")
    print(f"{'Agent pipeline':<30} {agent_accuracy:>19.1%}")
    print(f"{'Duplicate detection':<30} {duplicate_accuracy:>19.1%}")
    print("=" * 50)

    report = {
        "agent_accuracy": agent_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "duplicate_accuracy": duplicate_accuracy,
        "agent_results": agent_results,
        "baseline_results": baseline_results,
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nResults saved to {args.output}")
