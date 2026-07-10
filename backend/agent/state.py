from typing import TypedDict, Optional, List


class TriageState(TypedDict):
    issue_number: int
    issue_title: str
    issue_body: str
    category: Optional[str]
    similar_issues: List[dict]
    relevant_code_files: List[dict]
    severity: Optional[str]
    draft_reply: Optional[str]
    needs_human_review: bool
    reasoning_log: List[str]
    route_taken: Optional[str]
