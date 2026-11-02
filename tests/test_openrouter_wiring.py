"""Offline configuration and client wiring tests; no paid API calls."""
import importlib
from unittest.mock import MagicMock, patch

def test_openrouter_configuration(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    from src import config
    importlib.reload(config)
    assert config.OPENROUTER_API_KEY == "test-key"
    assert config.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"

def test_llm_uses_openrouter(monkeypatch):
    from src import llm_analyzer
    llm_analyzer.get_structured_llm.cache_clear()
    monkeypatch.setattr(llm_analyzer, "OPENROUTER_API_KEY", "test-key")
    fake = MagicMock()
    with patch.object(llm_analyzer, "ChatOpenAI", return_value=fake) as ctor:
        llm_analyzer.get_structured_llm()
    assert ctor.call_args.kwargs["api_key"] == "test-key"
    assert ctor.call_args.kwargs["base_url"] == "https://openrouter.ai/api/v1"
    fake.with_structured_output.assert_called_once_with(llm_analyzer.CallAnalysisResponse)
    llm_analyzer.get_structured_llm.cache_clear()

def test_embeddings_use_openrouter(monkeypatch, tmp_path):
    from src import rag_engine
    rag_engine.build_or_load_vector_db.cache_clear()
    monkeypatch.setattr(rag_engine, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(rag_engine, "VECTOR_DB_DIR", tmp_path)
    (tmp_path / "index.faiss").touch()
    fake = MagicMock()
    with patch.object(rag_engine, "OpenAIEmbeddings") as embeddings, patch.object(rag_engine.FAISS, "load_local", return_value=fake):
        rag_engine.build_or_load_vector_db()
    assert embeddings.call_args.kwargs["api_key"] == "test-key"
    assert embeddings.call_args.kwargs["base_url"] == "https://openrouter.ai/api/v1"
    assert embeddings.call_args.kwargs["check_embedding_ctx_length"] is False
    rag_engine.build_or_load_vector_db.cache_clear()
