"""CLI script to test the triage agent on a single issue."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from agent.graph import triage_graph
from config import DATA_DIR


def run_from_sample(issue_number: int):
    sample_path = DATA_DIR / "sample_issues.json"
    if not sample_path.exists():
        print(f"Error: {sample_path} not found")
        sys.exit(1)

    with open(sample_path) as f:
        issues = json.load(f)

    issue = next((i for i in issues if i["number"] == issue_number), None)
    if not issue:
        print(f"Issue #{issue_number} not found in sample data")
        sys.exit(1)

    return triage_graph.invoke(
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


def run_custom(title: str, body: str, issue_number: int = 0):
    return triage_graph.invoke(
        {
            "issue_number": issue_number,
            "issue_title": title,
            "issue_body": body,
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test RepoTriage agent")
    parser.add_argument("--issue-number", type=int, help="Issue number from sample_issues.json")
    parser.add_argument("--title", help="Custom issue title")
    parser.add_argument("--body", default="", help="Custom issue body")
    args = parser.parse_args()

    if args.issue_number:
        result = run_from_sample(args.issue_number)
    elif args.title:
        result = run_custom(args.title, args.body)
    else:
        result = run_custom(
            "Login button freezes after click",
            "When I click the login button, the page freezes. Console shows: undefined is not a function",
            issue_number=9999,
        )

    print("\n" + "=" * 60)
    print("TRIAGE RESULT")
    print("=" * 60)
    print(f"Category:  {result.get('category')}")
    print(f"Severity:  {result.get('severity')}")
    print(f"Route:     {result.get('route_taken')}")
    print(f"\nSimilar Issues:")
    for s in result.get("similar_issues", []):
        print(f"  #{s.get('number')} - {s.get('title')} (score={s.get('score')})")
    print(f"\nRelevant Code:")
    for c in result.get("relevant_code_files", []):
        print(f"  {c.get('file')}")
    print(f"\nReasoning Log:")
    for step in result.get("reasoning_log", []):
        print(f"  → {step}")
    print(f"\nDraft Reply:")
    print("-" * 60)
    print(result.get("draft_reply", "(none)"))
    print("=" * 60)
