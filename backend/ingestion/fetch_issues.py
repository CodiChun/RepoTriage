"""Fetch historical GitHub issues for evaluation and vector store seeding."""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from github import Github

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def fetch_issues(repo_name: str, limit: int = 200, output: str | None = None) -> list[dict]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set in backend/.env")
        sys.exit(1)

    g = Github(token)
    repo = g.get_repo(repo_name)

    issues = []
    for issue in repo.get_issues(state="all", sort="created"):
        if issue.pull_request:
            continue

        comments = []
        try:
            for c in issue.get_comments()[:3]:
                comments.append(c.body)
        except Exception:
            pass

        issues.append(
            {
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "labels": [label.name for label in issue.labels],
                "state": issue.state,
                "comments": comments,
                "closed_reason": "duplicate"
                if any("duplicate" in label.name.lower() for label in issue.labels)
                else None,
            }
        )

        if len(issues) >= limit:
            break

    output_path = Path(output) if output else DATA_DIR / "sample_issues.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(issues, f, indent=2)

    print(f"Fetched {len(issues)} issues from {repo_name} -> {output_path}")
    return issues


def build_issue_vectorstore():
    """Build or rebuild the issue vector store from sample_issues.json."""
    from agent.tools import get_embedding_model, _load_issue_documents
    from agent.vectorstore import SimpleVectorStore
    from config import CHROMA_DIR

    docs = _load_issue_documents()
    if not docs:
        print("No issue documents found. Run fetch_issues first.")
        sys.exit(1)

    persist_dir = str(CHROMA_DIR / "issues")
    embedding = get_embedding_model()
    SimpleVectorStore.from_documents(docs, embedding, persist_dir)
    print(f"Built issue vectorstore with {len(docs)} documents -> {persist_dir}")


def build_code_vectorstore(repo_name: str | None = None):
    """Build or rebuild the code vector store from a GitHub repo."""
    from agent.tools import get_embedding_model
    from agent.vectorstore import SimpleVectorStore
    from config import CHROMA_DIR, GITHUB_REPO, GITHUB_TOKEN
    from langchain_community.document_loaders import GithubFileLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    repo = repo_name or GITHUB_REPO
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN not set")
        sys.exit(1)

    loader = GithubFileLoader(
        repo=repo,
        access_token=GITHUB_TOKEN,
        file_filter=lambda path: path.endswith((".py", ".ts", ".tsx", ".js", ".go", ".rs")),
    )
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    persist_dir = str(CHROMA_DIR / "code")
    embedding = get_embedding_model()
    SimpleVectorStore.from_documents(chunks, embedding, persist_dir)
    print(f"Built code vectorstore with {len(chunks)} chunks from {repo} -> {persist_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoTriage data ingestion")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_parser = sub.add_parser("fetch", help="Fetch issues from GitHub")
    fetch_parser.add_argument("--repo", default=os.getenv("GITHUB_REPO", "owner/repo_name"))
    fetch_parser.add_argument("--limit", type=int, default=200)
    fetch_parser.add_argument("--output", default=None)

    sub.add_parser("build-issues", help="Build issue vector store from sample_issues.json")
    build_code_parser = sub.add_parser("build-code", help="Build code vector store from GitHub repo")
    build_code_parser.add_argument("--repo", default=None)

    args = parser.parse_args()

    if args.command == "fetch":
        fetch_issues(args.repo, args.limit, args.output)
    elif args.command == "build-issues":
        build_issue_vectorstore()
    elif args.command == "build-code":
        build_code_vectorstore(args.repo)
