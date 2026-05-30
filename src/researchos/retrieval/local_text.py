from __future__ import annotations

import re

from researchos.models.run import ResearchDocument
from researchos.retrieval.base import RetrievedChunk


class LocalKeywordRetriever:
    def __init__(self, *, max_chunk_chars: int = 600):
        self.max_chunk_chars = max_chunk_chars

    def retrieve(
        self,
        query: str,
        documents: list[ResearchDocument],
        *,
        limit: int = 3,
    ) -> list[RetrievedChunk]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return []

        chunks: list[RetrievedChunk] = []
        for document_index, document in enumerate(documents):
            title_terms = set(tokenize(document.title))
            for chunk in chunk_text(document.text, max_chars=self.max_chunk_chars):
                chunk_terms = set(tokenize(chunk))
                overlap = query_terms & chunk_terms
                title_overlap = query_terms & title_terms
                score = (len(overlap) + len(title_overlap) * 0.5) / len(query_terms)
                chunks.append(
                    RetrievedChunk(
                        document_index=document_index,
                        title=document.title,
                        text=chunk,
                        score=round(score, 4),
                        url=document.url,
                    )
                )

        ranked = sorted(chunks, key=lambda chunk: chunk.score, reverse=True)
        positive = [chunk for chunk in ranked if chunk.score > 0]
        return positive[:limit]


def retrieve_local_text(
    query: str,
    documents: list[ResearchDocument],
    *,
    limit: int = 3,
) -> list[RetrievedChunk]:
    return LocalKeywordRetriever().retrieve(query, documents, limit=limit)


def chunk_text(text: str, *, max_chars: int = 600) -> list[str]:
    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()
    ]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 > max_chars and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            chunks.append(current.strip())
    return chunks


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())
