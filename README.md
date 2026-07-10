# RepoTriage

An AI agent that automatically analyzes GitHub issues — demonstrating agentic workflows, tool calling, RAG, and human-in-the-loop review.

> Classify issues → detect duplicates → find relevant code → draft replies → human approval before posting.

## Architecture

```
GitHub Issue
    │
    ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Classify   │───▶│ Find Similar │───▶│  Find Code  │
│   (LLM)     │    │  (RAG/issues)│    │  (RAG/code) │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Router    │
                                        │  (decision) │
                                        └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
            duplicate_path            bug_analysis_path              answer_path
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               ▼
                                        ┌─────────────┐
                                        │ Draft Reply │
                                        │   (LLM)     │
                                        └──────┬──────┘
                                               ▼
                                        Human Review (Dashboard)
                                               ▼
                                        Post to GitHub
```

**Tech stack:** LangGraph · LangChain · ChromaDB · FastAPI · Next.js · SQLAlchemy

## Quick Start

### 1. Environment Setup

```bash
cd RepoTriage
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your GITHUB_TOKEN and ANTHROPIC_API_KEY (or OPENAI_API_KEY)
```

### 3. Fetch Test Data (optional — sample data included)

```bash
cd backend
python -m ingestion.fetch_issues fetch --repo owner/repo_name --limit 200
python -m ingestion.fetch_issues build-issues
python -m ingestion.fetch_issues build-code --repo owner/repo_name
```

### 4. Run the Agent (CLI)

```bash
cd backend
python run_triage.py                                    # demo issue
python run_triage.py --issue-number 101                 # from sample data
python run_triage.py --title "Bug report" --body "..."  # custom issue
```

### 5. Start Backend API

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 6. Start Frontend Dashboard

```bash
cd frontend
# cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Evaluation

Compare agent pipeline vs zero-shot LLM baseline:

```bash
cd backend
python -m eval.run_eval --limit 15 --output ../data/eval_results.json
```

Example output:

| Method | Classification Accuracy |
|---|---|
| Zero-shot LLM baseline | ~68% |
| Agent pipeline | ~89% |
| Duplicate detection | ~82% |

*Actual numbers depend on your target repo and API keys.*

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/triage` | Manually trigger triage on an issue |
| `POST` | `/webhook/github` | GitHub webhook for new issues |
| `GET` | `/issues` | List all triaged issues |
| `GET` | `/issues/pending-review` | Issues awaiting human review |
| `GET` | `/issues/{id}` | Get triage detail with reasoning log |
| `POST` | `/issues/{id}/approve` | Approve and post reply to GitHub |
| `POST` | `/issues/{id}/reject` | Reject draft reply |

## Project Structure

```
RepoTriage/
├── backend/
│   ├── agent/
│   │   ├── graph.py          # LangGraph workflow
│   │   ├── nodes.py          # Agent node logic
│   │   ├── tools.py          # GitHub API + vector stores
│   │   └── state.py          # Agent state definition
│   ├── ingestion/
│   │   └── fetch_issues.py   # Fetch issues + build vector stores
│   ├── eval/
│   │   └── run_eval.py       # Evaluation vs baseline
│   ├── db/
│   │   └── models.py         # SQLAlchemy models
│   ├── main.py               # FastAPI entry
│   └── run_triage.py         # CLI test script
├── frontend/                  # Next.js dashboard
├── data/
│   └── sample_issues.json    # Test data (15 sample issues)
└── requirements.txt
```

## Design Decisions

**Why LangGraph?** The triage workflow has conditional routing (duplicate vs bug vs question). LangGraph makes this explicit and debuggable — each step is a node with visible state transitions.

**Why human-in-the-loop?** AI-generated replies should never auto-post to public repos. The dashboard lets maintainers review, edit, and approve before anything goes live.

**Why RAG?** Zero-shot LLM classification misses context from similar past issues and relevant source code. Vector search grounds the agent's decisions in real project history.

## Deployment

- **Frontend:** Vercel (`cd frontend && vercel`)
- **Backend:** Railway or Render
- **Database:** Railway Postgres or Supabase (update `DATABASE_URL` in `.env`)

## License

