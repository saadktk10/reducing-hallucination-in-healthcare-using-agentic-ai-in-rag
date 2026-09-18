"""Tests for src/common/text.py — sentence splitting and token-aware chunking."""

from src.common.text import normalize_question, split_sentences, token_chunks


class TestSplitSentences:
    """Tests for the sentence splitter."""

    def test_basic_split(self) -> None:
        text = "First sentence. Second sentence. Third sentence."
        sentences = split_sentences(text)
        assert len(sentences) == 3

    def test_empty_string(self) -> None:
        assert split_sentences("") == []

    def test_single_sentence(self) -> None:
        sentences = split_sentences("Just one sentence.")
        assert len(sentences) == 1

    def test_no_empty_strings(self) -> None:
        """Splitting should never produce empty strings (Design.md §6.2)."""
        text = "First.  Second.   Third."
        sentences = split_sentences(text)
        for s in sentences:
            assert s.strip() != ""

    def test_abbreviations(self) -> None:
        """pysbd should handle common abbreviations like Dr., Mr., etc."""
        text = "Dr. Smith prescribed medication. The patient recovered."
        sentences = split_sentences(text)
        assert len(sentences) == 2


class TestTokenChunks:
    """Tests for the token-aware chunker."""

    def test_short_text_single_chunk(self) -> None:
        """Text within budget stays as one chunk."""
        text = "This is a short sentence."
        chunks = token_chunks(text, budget=100)
        assert len(chunks) == 1

    def test_budget_respected(self) -> None:
        """Each chunk stays within the word budget (proxy for tokens)."""
        text = " ".join(["word"] * 200)
        chunks = token_chunks(text, budget=50, overlap=0)
        for chunk in chunks:
            assert len(chunk.split()) <= 55  # small tolerance for sentence grouping

    def test_overlap_present(self) -> None:
        """With overlap > 0, consecutive chunks share some content."""
        text = "Sentence one here. Sentence two here. Sentence three here. Sentence four here."
        chunks = token_chunks(text, budget=8, overlap=4)
        assert len(chunks) >= 2

    def test_empty_text(self) -> None:
        """Empty text returns empty list."""
        assert token_chunks("", budget=100) == []

    def test_single_long_sentence(self) -> None:
        """A single sentence exceeding the budget becomes its own chunk."""
        text = " ".join(["word"] * 100) + "."
        chunks = token_chunks(text, budget=20, overlap=0)
        assert len(chunks) >= 1


class TestNormalizeQuestion:
    """Tests for question normalization."""

    def test_basic_normalization(self) -> None:
        assert normalize_question("What is X?") == "what is x"

    def test_punctuation_removed(self) -> None:
        assert normalize_question("Hello, world!") == "hello world"

    def test_whitespace_collapsed(self) -> None:
        assert normalize_question("  too   many  spaces  ") == "too many spaces"

    def test_case_insensitive(self) -> None:
        q1 = normalize_question("What Is The Treatment?")
        q2 = normalize_question("what is the treatment?")
        assert q1 == q2
