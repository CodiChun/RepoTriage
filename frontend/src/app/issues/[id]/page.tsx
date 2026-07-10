"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchIssue,
  approveReply,
  rejectReply,
  type TriageResult,
} from "@/lib/api";

const ROUTE_LABELS: Record<string, string> = {
  duplicate_path: "Duplicate Detection",
  bug_analysis_path: "Bug Analysis",
  answer_path: "Question Answering",
  need_more_info_path: "Request More Info",
};

export default function IssueDetailPage() {
  const params = useParams();
  const id = Number(params.id);

  const [issue, setIssue] = useState<TriageResult | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIssue(id)
      .then((data) => {
        setIssue(data);
        setDraft(data.draft_reply || "");
      })
      .catch(() => setError("Failed to load issue"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleApprove = async () => {
    setActing(true);
    try {
      const updated = await approveReply(id, draft);
      setIssue(updated);
    } catch {
      setError("Failed to approve. Check GitHub token if posting comment.");
    } finally {
      setActing(false);
    }
  };

  const handleReject = async () => {
    setActing(true);
    try {
      const updated = await rejectReply(id);
      setIssue(updated);
    } catch {
      setError("Failed to reject");
    } finally {
      setActing(false);
    }
  };

  if (loading) return <div className="container"><p className="empty-state">Loading...</p></div>;
  if (!issue) return <div className="container"><p className="empty-state">{error || "Not found"}</p></div>;

  return (
    <div className="container">
      <header className="header">
        <div>
          <Link href="/" style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
            ← Back to list
          </Link>
          <h1 style={{ marginTop: "0.5rem" }}>
            Issue #{issue.issue_number}
          </h1>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {issue.category && (
            <span className={`badge badge-${issue.category}`}>{issue.category}</span>
          )}
          {issue.severity && (
            <span className="badge badge-pending">{issue.severity} severity</span>
          )}
          <span className={`badge badge-${issue.review_status}`}>{issue.review_status}</span>
        </div>
      </header>

      <div className="detail-grid">
        {/* Left: Original Issue */}
        <div className="card">
          <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Original Issue</h2>
          <h3 style={{ fontWeight: 600, marginBottom: "0.75rem" }}>{issue.issue_title}</h3>
          <div className="code-snippet" style={{ whiteSpace: "pre-wrap" }}>
            {issue.issue_body || "(empty body)"}
          </div>
        </div>

        {/* Right: Agent Reasoning */}
        <div className="card">
          <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>
            Agent Decision Process
          </h2>

          {issue.route_taken && (
            <div
              style={{
                padding: "0.75rem 1rem",
                background: "rgba(108, 140, 255, 0.1)",
                borderRadius: "8px",
                marginBottom: "1rem",
                border: "1px solid var(--accent-dim)",
              }}
            >
              <strong>Route taken:</strong> {ROUTE_LABELS[issue.route_taken] || issue.route_taken}
            </div>
          )}

          {issue.reasoning_log.map((step, i) => (
            <div className="reasoning-step" key={i}>
              <div className="step-number">{i + 1}</div>
              <div className="step-content">
                <p>{step}</p>
              </div>
            </div>
          ))}

          {issue.similar_issues.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <h3 style={{ fontSize: "0.875rem", marginBottom: "0.5rem", color: "var(--text-muted)" }}>
                Similar Issues
              </h3>
              {issue.similar_issues.map((s) => (
                <div key={s.number} className="code-snippet" style={{ marginBottom: "0.5rem" }}>
                  #{s.number} — {s.title} (score: {s.score})
                </div>
              ))}
            </div>
          )}

          {issue.relevant_code_files.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <h3 style={{ fontSize: "0.875rem", marginBottom: "0.5rem", color: "var(--text-muted)" }}>
                Relevant Code
              </h3>
              {issue.relevant_code_files.map((f, i) => (
                <div key={i} style={{ marginBottom: "0.5rem" }}>
                  <p style={{ fontSize: "0.8rem", color: "var(--accent)", marginBottom: "0.25rem" }}>
                    {f.file}
                  </p>
                  <div className="code-snippet">{f.snippet}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Draft Reply */}
      <div className="card" style={{ marginTop: "1.5rem" }}>
        <h2 style={{ fontSize: "1rem", marginBottom: "1rem" }}>Draft Reply</h2>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={issue.review_status === "posted" || issue.review_status === "rejected"}
        />
        {error && <p style={{ color: "var(--danger)", marginTop: "0.5rem", fontSize: "0.875rem" }}>{error}</p>}
        {issue.review_status === "pending" && (
          <div className="actions">
            <button className="btn btn-primary" onClick={handleApprove} disabled={acting}>
              {acting ? "Posting..." : "Approve & Post to GitHub"}
            </button>
            <button className="btn btn-danger" onClick={handleReject} disabled={acting}>
              Reject
            </button>
          </div>
        )}
        {issue.github_comment_url && (
          <p style={{ marginTop: "1rem", fontSize: "0.875rem" }}>
            Posted: <a href={issue.github_comment_url} target="_blank" rel="noopener noreferrer">
              View on GitHub
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
