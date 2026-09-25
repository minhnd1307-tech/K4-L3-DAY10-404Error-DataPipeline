import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from core.config import load_settings
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.llm import build_llm
from retrieval.qa import answer_question
from retrieval.agent import build_agent


def test_minilm_embeddings():
    """Kiểm tra mô hình MiniLM tạo embedding chuẩn 384 chiều và L2-norm xấp xỉ 1."""
    embed_model = MiniLMEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
    vec = embed_model.embed_query("Data pipeline and observability test")

    assert isinstance(vec, list)
    assert len(vec) == 384
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0, atol=1e-3), f"Vector norm {norm} should be close to 1.0"


def test_chroma_build_and_search(tmp_path):
    """Kiểm tra ChromaDB build index và semantic search với dummy data."""
    settings = load_settings()

    dummy_data = [
        {
            "paper_id": "10.1000/test.1",
            "title": "Machine Learning in Production",
            "summary": "This paper discusses MLOps and automated pipelines for reliable AI systems.",
            "authors_joined": "Nguyen Van A, Tran Van B",
            "categories_joined": "cs.AI, cs.LG",
            "published": "2024-01-15",
            "abs_url": "https://doi.org/10.1000/test.1",
            "pdf_url": "https://doi.org/10.1000/test.1.pdf",
            "text_for_embedding": "Title: Machine Learning in Production\nAuthors: Nguyen Van A\nSummary: MLOps and pipelines.",
        },
        {
            "paper_id": "10.1000/test.2",
            "title": "Deep Learning for Natural Language Processing",
            "summary": "An extensive survey on transformer architectures and large language models.",
            "authors_joined": "Le Van C",
            "categories_joined": "cs.CL",
            "published": "2023-11-20",
            "abs_url": "https://doi.org/10.1000/test.2",
            "pdf_url": "https://doi.org/10.1000/test.2.pdf",
            "text_for_embedding": "Title: Deep Learning for Natural Language Processing\nSummary: Transformer architectures survey.",
        },
    ]
    df = pd.DataFrame(dummy_data)
    manifest_path = tmp_path / "test_embeddings.json"

    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=manifest_path)
    assert len(index.documents) == 2
    assert manifest_path.exists()

    # Test semantic search
    results = index.search("MLOps and automated pipelines", top_k=2)
    assert len(results) > 0
    assert results[0].paper_id == "10.1000/test.1"
    assert results[0].score > 0.0

    # Test exact lookup
    lookup_res = index.lookup("10.1000/test.1")
    assert lookup_res is not None
    assert lookup_res["title"] == "Machine Learning in Production"


def test_mock_llm_and_qa_agent(tmp_path):
    """Kiểm tra LLM provider mock và khởi tạo QA Agent không bị crash."""
    settings = load_settings()

    dummy_data = [
        {
            "paper_id": "10.1000/test.1",
            "title": "Machine Learning in Production",
            "summary": "This paper discusses MLOps and automated pipelines for reliable AI systems.",
            "authors_joined": "Nguyen Van A, Tran Van B",
            "categories_joined": "cs.AI, cs.LG",
            "published": "2024-01-15",
            "abs_url": "https://doi.org/10.1000/test.1",
            "pdf_url": "https://doi.org/10.1000/test.1.pdf",
            "text_for_embedding": "Title: Machine Learning in Production\nSummary: MLOps and pipelines.",
        }
    ]
    df = pd.DataFrame(dummy_data)
    index = LocalEmbeddingIndex.build(df, settings, embeddings_output_path=tmp_path / "manifest.json")

    # Test answer_question
    ans = answer_question("Who authored 'Machine Learning in Production'?", settings, index)
    assert ans.answer == "Nguyen Van A, Tran Van B"
    assert "10.1000/test.1" in ans.retrieved_doc_ids

    # Test mock LLM
    import dataclasses
    mock_settings = dataclasses.replace(settings, llm_provider="mock")
    llm = build_llm(mock_settings)
    assert llm is not None

    agent = build_agent(mock_settings, index)
    assert agent is not None
