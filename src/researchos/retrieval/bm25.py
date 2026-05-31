from __future__ import annotations

import math
from collections import Counter

from researchos.models.run import ResearchDocument
from researchos.retrieval.base import RetrievedChunk
from researchos.retrieval.local_text import chunk_text, tokenize


class BM25Retriever:
    strategy_name = "bm25"
    score_type = "bm25"

    def __init__(
        self,
        *,
        max_chunk_chars: int = 600,
        chunk_overlap_chars: int = 0,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self.k1 = k1
        self.b = b

    def retrieve(
        self,
        query: str,
        documents: list[ResearchDocument],
        *,
        limit: int = 3,
    ) -> list[RetrievedChunk]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        corpus = self._build_corpus(documents)
        if not corpus:
            return []

        avg_doc_len = sum(len(item.terms) for item in corpus) / len(corpus)
        document_frequency = self._document_frequency(corpus)
        scored_chunks = [
            RetrievedChunk(
                document_index=item.document_index,
                title=item.title,
                text=item.text,
                score=round(
                    self._score(
                        query_terms,
                        item.term_counts,
                        len(item.terms),
                        avg_doc_len,
                        document_frequency,
                        len(corpus),
                    ),
                    4,
                ),
                url=item.url,
            )
            for item in corpus
        ]
        ranked = sorted(scored_chunks, key=lambda chunk: chunk.score, reverse=True)
        positive = [chunk for chunk in ranked if chunk.score > 0]
        return positive[:limit]

    def _build_corpus(self, documents: list[ResearchDocument]) -> list[_CorpusItem]:
        corpus: list[_CorpusItem] = []
        for document_index, document in enumerate(documents):
            for chunk in chunk_text(
                document.text,
                max_chars=self.max_chunk_chars,
                overlap_chars=self.chunk_overlap_chars,
            ):
                title_terms = tokenize(document.title)
                chunk_terms = tokenize(chunk)
                terms = title_terms + chunk_terms
                corpus.append(
                    _CorpusItem(
                        document_index=document_index,
                        title=document.title,
                        text=chunk,
                        url=document.url,
                        terms=terms,
                        term_counts=Counter(terms),
                    )
                )
        return corpus

    def _document_frequency(self, corpus: list[_CorpusItem]) -> dict[str, int]:
        frequency: dict[str, int] = {}
        for item in corpus:
            for term in set(item.terms):
                frequency[term] = frequency.get(term, 0) + 1
        return frequency

    def _score(
        self,
        query_terms: list[str],
        term_counts: Counter[str],
        doc_len: int,
        avg_doc_len: float,
        document_frequency: dict[str, int],
        corpus_size: int,
    ) -> float:
        score = 0.0
        for term in query_terms:
            term_frequency = term_counts.get(term, 0)
            if term_frequency == 0:
                continue

            idf = math.log(
                1 + (corpus_size - document_frequency.get(term, 0) + 0.5)
                / (document_frequency.get(term, 0) + 0.5)
            )
            denominator = term_frequency + self.k1 * (
                1 - self.b + self.b * doc_len / avg_doc_len
            )
            score += idf * (term_frequency * (self.k1 + 1)) / denominator
        return score


class _CorpusItem:
    def __init__(
        self,
        *,
        document_index: int,
        title: str,
        text: str,
        url: str | None,
        terms: list[str],
        term_counts: Counter[str],
    ):
        self.document_index = document_index
        self.title = title
        self.text = text
        self.url = url
        self.terms = terms
        self.term_counts = term_counts
