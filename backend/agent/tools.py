import os
from typing import Optional

from github import Github
from langchain_community.document_loaders import GithubFileLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from agent.vectorstore import SimpleVectorStore
from config import (
    CHROMA_DIR,
    DATA_DIR,
    DUPLICATE_SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    GITHUB_REPO,
    GITHUB_TOKEN,
)


def get_embedding_model():
    if EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=EMBEDDING_MODEL)

    # Runs sentence-transformers/all-MiniLM-L6-v2 locally via ONNX (no torch/API key needed).
    # Falls back to sentence-transformers if torch is installed on the system.
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    except Exception:
        from langchain_community.embeddings import FastEmbedEmbeddings
        return FastEmbedEmbeddings(model_name=EMBEDDING_MODEL)


def get_github_client() -> Github:
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN is not set. Copy backend/.env.example to backend/.env")
    return Github(GITHUB_TOKEN)


def post_comment_to_github(issue_number: int, body: str, repo_name: Optional[str] = None) -> dict:
    """Post an approved reply as a GitHub issue comment."""
    g = get_github_client()
    repo = g.get_repo(repo_name or GITHUB_REPO)
    issue = repo.get_issue(issue_number)
    comment = issue.create_comment(body)
    return {"comment_id": comment.id, "url": comment.html_url}


def _load_issue_documents() -> list[Document]:
    import json

    sample_path = DATA_DIR / "sample_issues.json"
    if not sample_path.exists():
        return []

    with open(sample_path) as f:
        issues = json.load(f)

    docs = []
    for issue in issues:
        text = f"{issue['title']}\n{issue.get('body') or ''}"
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "number": issue["number"],
                    "title": issue["title"],
                    "labels": issue.get("labels", []),
                    "state": issue.get("state", "open"),
                },
            )
        )
    return docs


def get_issue_vectorstore() -> Optional[SimpleVectorStore]:
    persist_dir = str(CHROMA_DIR / "issues")
    embedding = get_embedding_model()

    store = SimpleVectorStore.load(embedding, persist_dir)
    if store:
        return store

    docs = _load_issue_documents()
    if not docs:
        return None

    return SimpleVectorStore.from_documents(docs, embedding, persist_dir)


def get_code_vectorstore() -> Optional[SimpleVectorStore]:
    persist_dir = str(CHROMA_DIR / "code")
    embedding = get_embedding_model()

    store = SimpleVectorStore.load(embedding, persist_dir)
    if store:
        return store

    if not GITHUB_TOKEN or GITHUB_REPO == "owner/repo_name":
        return None

    loader = GithubFileLoader(
        repo=GITHUB_REPO,
        access_token=GITHUB_TOKEN,
        file_filter=lambda path: path.endswith((".py", ".ts", ".tsx", ".js", ".go", ".rs")),
    )
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    return SimpleVectorStore.from_documents(chunks, embedding, persist_dir)


def similarity_search_with_score(vectorstore: SimpleVectorStore, query: str, k: int = 3) -> list[dict]:
    """Search vectorstore and return results with distance-based scores."""
    results = vectorstore.similarity_search_with_score(query, k=k)
    formatted = []
    for doc, distance in results:
        score = max(0.0, 1.0 - distance)
        formatted.append(
            {
                "content": doc.page_content[:300],
                "metadata": doc.metadata,
                "score": round(score, 4),
            }
        )
    return formatted


def is_likely_duplicate(similar_issues: list[dict], threshold: float = DUPLICATE_SIMILARITY_THRESHOLD) -> bool:
    if not similar_issues:
        return False
    return similar_issues[0].get("score", 0) > threshold
