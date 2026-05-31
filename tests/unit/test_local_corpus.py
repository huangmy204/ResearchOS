from __future__ import annotations

import pytest

from researchos.ingestion import LocalCorpusLoader


def test_local_corpus_loader_reads_markdown_and_text_files(tmp_path):
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "legal.md").write_text(
        "# Legal Citation Memo\n\nUnsupported citations create legal risk.",
        encoding="utf-8",
    )
    (corpus_root / "finance.txt").write_text(
        "Revenue recognition memos require evidence.",
        encoding="utf-8",
    )
    (corpus_root / "ignored.pdf").write_text("not supported", encoding="utf-8")

    loaded = LocalCorpusLoader(corpus_root).load()

    assert [document.title for document in loaded.documents] == ["finance", "Legal Citation Memo"]
    assert [file.path for file in loaded.files] == ["finance.txt", "legal.md"]
    assert loaded.documents[1].url == "corpus://legal.md"


def test_local_corpus_loader_rejects_path_traversal(tmp_path):
    loader = LocalCorpusLoader(tmp_path / "corpus")

    with pytest.raises(ValueError, match="escapes"):
        loader.load(relative_paths=["../secret.txt"])


def test_local_corpus_loader_can_load_selected_relative_paths(tmp_path):
    corpus_root = tmp_path / "corpus"
    (corpus_root / "notes").mkdir(parents=True)
    (corpus_root / "notes" / "legal.txt").write_text(
        "Legal citation verification evidence.",
        encoding="utf-8",
    )
    (corpus_root / "other.txt").write_text("Other evidence.", encoding="utf-8")

    loaded = LocalCorpusLoader(corpus_root).load(relative_paths=["notes/legal.txt"])

    assert len(loaded.documents) == 1
    assert loaded.files[0].path == "notes/legal.txt"


def test_local_corpus_loader_lists_files_without_creating_documents(tmp_path):
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "memo.md").write_text("# Research Memo\n\nEvidence text.", encoding="utf-8")

    files = LocalCorpusLoader(corpus_root).list_files()

    assert len(files) == 1
    assert files[0].path == "memo.md"
    assert files[0].title == "Research Memo"
    assert files[0].suffix == ".md"
