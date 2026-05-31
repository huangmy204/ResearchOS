from __future__ import annotations

from researchos.ingestion import LocalCorpusIndex, LocalCorpusLoader


def test_local_corpus_index_builds_manifest_with_hashes(tmp_path):
    corpus_root = tmp_path / "corpus"
    loader = LocalCorpusLoader(corpus_root)
    loader.write_document(
        title="Legal Citation Risk",
        text="Unsupported citations create legal risk.",
    )

    manifest = LocalCorpusIndex(corpus_root).build()

    assert manifest.version == 1
    assert manifest.document_count == 1
    assert manifest.entries[0].path == "legal-citation-risk.md"
    assert manifest.entries[0].title == "Legal Citation Risk"
    assert len(manifest.entries[0].content_sha256) == 64
    assert manifest.entries[0].status == "ready"


def test_local_corpus_index_can_read_persisted_manifest(tmp_path):
    corpus_root = tmp_path / "corpus"
    loader = LocalCorpusLoader(corpus_root)
    loader.write_document(title="Finance Memo", text="Revenue evidence.")
    corpus_index = LocalCorpusIndex(corpus_root)
    corpus_index.build()

    loaded = LocalCorpusIndex(corpus_root).read()

    assert loaded.document_count == 1
    assert loaded.entries[0].path == "finance-memo.md"


def test_local_corpus_index_returns_empty_manifest_before_build(tmp_path):
    manifest = LocalCorpusIndex(tmp_path / "corpus").read()

    assert manifest.indexed_at is None
    assert manifest.document_count == 0
    assert manifest.entries == []


def test_local_corpus_index_hash_changes_when_document_changes(tmp_path):
    corpus_root = tmp_path / "corpus"
    loader = LocalCorpusLoader(corpus_root)
    loader.write_document(title="Legal Memo", text="First version.")
    corpus_index = LocalCorpusIndex(corpus_root)
    first = corpus_index.build()

    loader.write_document(
        title="Legal Memo",
        text="Second version.",
        overwrite=True,
    )
    second = corpus_index.build()

    assert first.entries[0].content_sha256 != second.entries[0].content_sha256
