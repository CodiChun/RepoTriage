# backend/test_agent.py
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from agent.graph import triage_graph

test_input = {
    "issue_number": 999,
    "issue_title": "Login button freezes after click",
    "issue_body": "Console shows undefined is not a function. Tested on Chrome.",
    "category": None,
    "similar_issues": [],
    "relevant_code_files": [],
    "severity": None,
    "draft_reply": None,
    "needs_human_review": False,
    "reasoning_log": [],
    "route_taken": None,
}

result = triage_graph.invoke(test_input)

print("=" * 50)
print("Category:", result["category"])
print("Similar issues found:", result["similar_issues"])
print("Relevant code found:", result["relevant_code_files"])
print("Generated draft reply:")
print(result["draft_reply"])
print("=" * 50)
print("Reasoning log:")
for log in result["reasoning_log"]:
    print(" -", log)
