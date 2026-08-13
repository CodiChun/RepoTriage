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

### Docker Compose (local)

```bash
cp .env.example .env   # set GITHUB_TOKEN, API keys, etc.
docker compose up --build
```

### Kubernetes (GKE)

Manifests live in [`k8s/`](k8s/) (Deployment, Service, PVC, ConfigMap). The frontend is exposed via a **LoadBalancer** Service; the backend stays internal and is reached through Next.js rewrites in the frontend pod.

**Prerequisites**

- A GKE cluster
- Docker Hub account with **public** images (`docker.io/codichun/repotriage-backend` and `repotriage-frontend`)

**One-time cluster setup**

1. Create application secrets:

```bash
kubectl create namespace repotriage --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic repotriage-secrets \
  --namespace repotriage \
  --from-literal=POSTGRES_USER=repotriage \
  --from-literal=POSTGRES_PASSWORD=change-me \
  --from-literal=POSTGRES_DB=repotriage \
  --from-literal=DATABASE_URL=postgresql://repotriage:change-me@postgres:5432/repotriage \
  --from-literal=GITHUB_TOKEN=ghp_xxx \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-xxx
```

2. Build and push images, then deploy:

```bash
docker build -t docker.io/codichun/repotriage-backend:latest .
docker build -t docker.io/codichun/repotriage-frontend:latest -f frontend/Dockerfile .
docker push docker.io/codichun/repotriage-backend:latest
docker push docker.io/codichun/repotriage-frontend:latest

kubectl apply -k k8s/
```

3. Get the external IP (no domain needed yet):

```bash
kubectl get svc frontend -n repotriage
# open http://<EXTERNAL-IP>:3000
```

When you add a domain later, point DNS at the LoadBalancer IP and tighten `CORS_ORIGINS` in [`k8s/configmap.yaml`](k8s/configmap.yaml).

**GitHub Actions auto-deploy**

Push to `main` runs [`.github/workflows/deploy-kubernetes.yml`](.github/workflows/deploy-kubernetes.yml), which builds images and applies manifests.

Configure these **GitHub Secrets** (Settings → Secrets and variables → Actions). The deploy job uses the **production** environment, so if that environment defines its own secrets, add them there as well.

A laptop `~/.kube/config` from `gcloud container clusters get-credentials` will not work in GitHub Actions: it calls `gke-gcloud-auth-plugin`, which is not on hosted runners. CI authenticates with a GCP service account and fetches short-lived cluster credentials instead.

```bash
PROJECT="$(gcloud config get-value project)"
gcloud iam service-accounts create github-deploy --project "${PROJECT}"
gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:github-deploy@${PROJECT}.iam.gserviceaccount.com" \
  --role="roles/container.developer"
gcloud iam service-accounts keys create sa.json \
  --iam-account="github-deploy@${PROJECT}.iam.gserviceaccount.com"
# Paste sa.json into secret GCP_SA_KEY, then delete sa.json
```

Also set Actions **variables** `GKE_CLUSTER` and `GKE_LOCATION` (region or zone). If you skip those, keep `KUBE_CONFIG` and the workflow will parse `gke_PROJECT_LOCATION_CLUSTER` from its current-context.

The GKE control plane must be reachable from GitHub-hosted runners (public endpoint; avoid locked-down authorized networks).

| Secret / variable | Description |
|---|---|
| `GCP_SA_KEY` | GCP service account JSON key with `roles/container.developer` |
| `GKE_CLUSTER` | GKE cluster name (variable preferred) |
| `GKE_LOCATION` | GKE region or zone (variable preferred) |
| `GCP_PROJECT` | Optional GCP project ID (inferred from the key if unset) |
| `KUBE_CONFIG` | Optional kubeconfig used only to discover cluster name/location |
| `DOCKER_USERNAME` | Docker Hub username (`codichun`) |
| `DOCKER_TOKEN` | Docker Hub access token |
| `POSTGRES_PASSWORD` | Postgres password for in-cluster DB (defaults to `repotriage` if unset) |
| `APP_GITHUB_TOKEN` | GitHub PAT for issue API (cannot use name `GITHUB_TOKEN`) |
| `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | LLM provider key |

Optional secrets/variables: `POSTGRES_USER`, `POSTGRES_DB`, `GITHUB_REPO`.

### Other options

- **Frontend:** Vercel (`cd frontend && vercel`)
- **Backend:** Railway or Render
- **Database:** Railway Postgres or Supabase (update `DATABASE_URL` in `.env`)

## License

