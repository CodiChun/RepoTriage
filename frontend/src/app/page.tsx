"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchIssues, triageIssue, type TriageResult } from "@/lib/api";

export default function HomePage() {
  const [issues, setIssues] = useState<TriageResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [triaging, setTriaging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const loadIssues = async () => {
    try {
      const data = await fetchIssues();
      setIssues(data);
      setError(null);
    } catch {
      setError("Cannot connect to backend. Make sure the API is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIssues();
  }, []);

  const handleTriage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setTriaging(true);
    try {
      await triageIssue({
        issue_number: Date.now(),
        issue_title: title,
        issue_body: body,
      });
      setTitle("");
      setBody("");
      await loadIssues();
    } catch {
      setError("Triage failed. Check your API keys in backend/.env");
    } finally {
      setTriaging(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1>
          <span>Repo</span>Triage
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
          AI-powered GitHub issue triage
        </p>
      </header>

      <form className="triage-form card" onSubmit={handleTriage}>
        <h2 style={{ fontSize: "1rem", marginBottom: "0.25rem" }}>Triage a New Issue</h2>
        <input
          placeholder="Issue title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="Issue body (optional)"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
        />
        <button className="btn btn-primary" type="submit" disabled={triaging}>
          {triaging ? "Analyzing..." : "Run Triage Agent"}
        </button>
      </form>

      {error && (
        <div className="card" style={{ borderColor: "var(--danger)", marginBottom: "1rem" }}>
          <p style={{ color: "var(--danger)" }}>{error}</p>
        </div>
      )}

      <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Triaged Issues</h2>

      {loading ? (
        <p className="empty-state">Loading...</p>
      ) : issues.length === 0 ? (
        <div className="empty-state">
          <p>No triaged issues yet.</p>
          <p style={{ marginTop: "0.5rem", fontSize: "0.875rem" }}>
            Submit an issue above or run <code>python run_triage.py</code> from the backend.
          </p>
        </div>
      ) : (
        <div className="card-grid">
          {issues.map((issue) => (
            <Link key={issue.id} href={`/issues/${issue.id}`}>
              <div className="card" style={{ cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                  <div>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
                      #{issue.issue_number}
                    </p>
                    <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>{issue.issue_title}</h3>
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
                    {issue.category && (
                      <span className={`badge badge-${issue.category}`}>{issue.category}</span>
                    )}
                    <span className={`badge badge-${issue.review_status}`}>{issue.review_status}</span>
                  </div>
                </div>
                {issue.route_taken && (
                  <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
                    Route: {issue.route_taken}
                  </p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
