from rag import HRPolicyRAG


def test_chunk_text_splits_long_text():
    text = ("Annual leave is governed by the employee handbook. " * 100)
    chunks = HRPolicyRAG.chunk_text(text, chunk_size=300, overlap=40)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_chunk_text_empty_input():
    assert HRPolicyRAG.chunk_text("  \n ") == []


def test_chunk_text_preserves_content():
    text = "Annual leave requires manager approval. Sick leave follows company policy."
    chunks = HRPolicyRAG.chunk_text(text, chunk_size=100, overlap=10)
    joined = " ".join(chunks)
    assert "Annual leave" in joined
    assert "Sick leave" in joined
