"""
Tests for Onboarding Mode.
All LLM calls are mocked — no Groq API calls made.
"""

import json
from unittest.mock import MagicMock, patch

from generation.onboarding import _build_codebase_summary, generate_onboarding_guide

# ── Fixtures ───────────────────────────────────────────────────────────────────

MOCK_GUIDE = {
    "summary": "A RAG-based codebase Q&A tool.",
    "entry_points": [
        {"file": "app.py", "reason": "Main Streamlit application entry point."}
    ],
    "reading_order": [
        {"step": 1, "file": "config.py", "why": "Understand all settings first."},
        {"step": 2, "file": "ingestion/loader.py", "why": "See how repos are cloned."},
    ],
    "glossary": [
        {"term": "RAG", "definition": "Retrieval Augmented Generation — search then answer."},
        {"term": "ChromaDB", "definition": "Vector database storing code embeddings."},
    ],
    "data_flow": "GitHub URL → loader → parser → embedder → ChromaDB → retriever → LLM → answer",
}


def make_mock_retriever(chunks=None):
    """Create a mock retriever that returns fake chunks."""
    if chunks is None:
        chunks = [
            {
                "file_path": "app.py",
                "type": "function",
                "name": "main",
                "content": "def main():\n    st.title('StackVault')\n",
                "start_line": 1,
                "end_line": 10,
                "score": 0.9,
            },
            {
                "file_path": "config.py",
                "type": "module",
                "name": "config",
                "content": "OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')\n",
                "start_line": 1,
                "end_line": 5,
                "score": 0.85,
            },
        ]
    retriever = MagicMock()
    retriever.search.return_value = chunks
    return retriever


# ── _build_codebase_summary ────────────────────────────────────────────────────

class TestBuildCodebaseSummary:
    def test_returns_string(self):
        retriever = make_mock_retriever()
        result = _build_codebase_summary(retriever)
        assert isinstance(result, str)

    def test_contains_file_paths(self):
        retriever = make_mock_retriever()
        result = _build_codebase_summary(retriever)
        assert "app.py" in result

    def test_deduplicates_files(self):
        # Same file returned multiple times — should appear only once
        chunk = {
            "file_path": "app.py",
            "type": "function",
            "name": "main",
            "content": "def main(): pass",
            "start_line": 1,
            "end_line": 5,
            "score": 0.9,
        }
        retriever = MagicMock()
        retriever.search.return_value = [chunk, chunk]
        result = _build_codebase_summary(retriever)
        assert result.count("FILE: app.py") == 1

    def test_respects_max_chars(self):
        # Large content should be truncated
        big_chunk = {
            "file_path": "big.py",
            "type": "function",
            "name": "big",
            "content": "x" * 50000,
            "start_line": 1,
            "end_line": 100,
            "score": 0.9,
        }
        retriever = MagicMock()
        retriever.search.return_value = [big_chunk]
        result = _build_codebase_summary(retriever)
        assert len(result) <= 12000

    def test_empty_retriever_returns_string(self):
        retriever = MagicMock()
        retriever.search.return_value = []
        result = _build_codebase_summary(retriever)
        assert isinstance(result, str)


# ── generate_onboarding_guide ──────────────────────────────────────────────────

class TestGenerateOnboardingGuide:
    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_returns_correct_keys(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(MOCK_GUIDE)
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)

        assert "summary" in result
        assert "entry_points" in result
        assert "reading_order" in result
        assert "glossary" in result
        assert "data_flow" in result

    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_entry_points_have_correct_fields(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(MOCK_GUIDE)
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)

        for ep in result["entry_points"]:
            assert "file" in ep
            assert "reason" in ep

    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_reading_order_has_steps(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(MOCK_GUIDE)
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)

        for item in result["reading_order"]:
            assert "step" in item
            assert "file" in item
            assert "why" in item

    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_glossary_has_term_and_definition(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(MOCK_GUIDE)
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)

        for item in result["glossary"]:
            assert "term" in item
            assert "definition" in item

    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_strips_markdown_code_fences(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = f"```json\n{json.dumps(MOCK_GUIDE)}\n```"
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)
        assert result["summary"] == MOCK_GUIDE["summary"]

    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_invalid_json_returns_fallback(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = "this is not json"
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)

        # Should not crash — returns fallback
        assert "summary" in result
        assert "entry_points" in result
        assert result["entry_points"] == []

    @patch("generation.onboarding.ChatGoogleGenerativeAI")
    def test_summary_is_string(self, mock_llm_class):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(MOCK_GUIDE)
        mock_llm_class.return_value = mock_llm

        retriever = make_mock_retriever()
        result = generate_onboarding_guide(retriever)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0
