export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TriageResult {
  id: number;
  issue_number: number;
  issue_title: string;
  issue_body: string | null;
  category: string | null;
  severity: string | null;
  similar_issues: Array<{ number: number; title: string; score: number }>;
  relevant_code_files: Array<{ file: string; snippet: string; score: number }>;
  draft_reply: string | null;
  reasoning_log: string[];
  route_taken: string | null;
  needs_human_review: boolean;
  review_status: string;
  github_comment_url: string | null;
  created_at: string;
}

export async function fetchIssues(): Promise<TriageResult[]> {
  const res = await fetch(`${API_BASE}/issues`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch issues");
  return res.json();
}

export async function fetchIssue(id: number): Promise<TriageResult> {
  const res = await fetch(`${API_BASE}/issues/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch issue");
  return res.json();
}

export async function triageIssue(data: {
  issue_number: number;
  issue_title: string;
  issue_body: string;
}): Promise<TriageResult> {
  const res = await fetch(`${API_BASE}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to triage issue");
  return res.json();
}

export async function approveReply(
  id: number,
  draft_reply?: string
): Promise<TriageResult> {
  const res = await fetch(`${API_BASE}/issues/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_reply }),
  });
  if (!res.ok) throw new Error("Failed to approve reply");
  return res.json();
}

export async function rejectReply(id: number): Promise<TriageResult> {
  const res = await fetch(`${API_BASE}/issues/${id}/reject`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to reject reply");
  return res.json();
}
