"""Lightweight vector store using pure Python — no numpy/ChromaDB dependency."""

import math
import pickle
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SimpleVectorStore:
    def __init__(self, embeddings: Embeddings, persist_dir: str):
        self.embeddings = embeddings
        self.persist_dir = Path(persist_dir)
        self.documents: list[Document] = []
        self.vectors: list[list[float]] = []

    def add_documents(self, documents: list[Document]):
        texts = [d.page_content for d in documents]
        self.vectors = self.embeddings.embed_documents(texts)
        self.documents = documents
        self._save()

    def similarity_search_with_score(self, query: str, k: int = 3) -> list[tuple[Document, float]]:
        if not self.documents or not self.vectors:
            return []

        query_vec = self.embeddings.embed_query(query)
        scores = [_cosine_similarity(query_vec, vec) for vec in self.vectors]
        distances = [1.0 - s for s in scores]

        ranked = sorted(range(len(distances)), key=lambda i: distances[i])
        return [(self.documents[i], distances[i]) for i in ranked[:k]]

    def _save(self):
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        with open(self.persist_dir / "store.pkl", "wb") as f:
            pickle.dump({"documents": self.documents, "vectors": self.vectors}, f)

    @classmethod
    def load(cls, embeddings: Embeddings, persist_dir: str) -> Optional["SimpleVectorStore"]:
        store_path = Path(persist_dir) / "store.pkl"
        if not store_path.exists():
            return None
        store = cls(embeddings, persist_dir)
        with open(store_path, "rb") as f:
            data = pickle.load(f)
        store.documents = data["documents"]
        store.vectors = data["vectors"]
        return store

    @classmethod
    def from_documents(cls, documents: list[Document], embeddings: Embeddings, persist_dir: str) -> "SimpleVectorStore":
        store = cls(embeddings, persist_dir)
        store.add_documents(documents)
        return store
