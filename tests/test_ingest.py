"""Tests for document ingestion module (Tasks 4.1-4.10)."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import json

from drhp_agent.ingest.loader import DocumentLoader
from drhp_agent.ingest.extractor import FactExtractor
from drhp_agent.core.exceptions import NotSupportedSourceTypeError
from drhp_agent.core.dtos import FactStore


class TestDocumentLoader:
    """Tests for DocumentLoader."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some markdown files
            Path(tmpdir, "doc1.md").write_text("# Document 1\nContent here")
            Path(tmpdir, "doc2.md").write_text("# Document 2\nMore content")

            # Create subdirectory with more files
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "doc3.md").write_text("# Document 3\nNested content")

            yield tmpdir

    def test_discover_finds_all_md_files(self, temp_dir):
        loader = DocumentLoader(temp_dir)
        files = loader.discover()
        assert len(files) == 3
        assert all(f.suffix == ".md" for f in files)

    def test_discover_recursive(self, temp_dir):
        loader = DocumentLoader(temp_dir)
        files = loader.discover()
        file_names = [f.name for f in files]
        assert "doc3.md" in file_names  # From subdirectory

    def test_discover_rejects_non_md_files(self, temp_dir):
        # Add a non-md file
        Path(temp_dir, "data.pdf").write_text("fake pdf")

        loader = DocumentLoader(temp_dir)
        with pytest.raises(NotSupportedSourceTypeError) as exc_info:
            loader.discover()
        assert ".pdf" in str(exc_info.value)

    def test_discover_ignores_hidden_files(self, temp_dir):
        # Add a hidden file
        Path(temp_dir, ".hidden").write_text("hidden")

        loader = DocumentLoader(temp_dir)
        files = loader.discover()
        assert len(files) == 3  # Only the 3 md files

    def test_read_file(self, temp_dir):
        loader = DocumentLoader(temp_dir)
        content = loader.read(Path(temp_dir, "doc1.md"))
        assert "# Document 1" in content
        assert "Content here" in content

    def test_read_utf8_file(self, temp_dir):
        # Create file with UTF-8 content
        Path(temp_dir, "unicode.md").write_text("# Unicode: ₹ € £", encoding="utf-8")

        loader = DocumentLoader(temp_dir)
        content = loader.read(Path(temp_dir, "unicode.md"))
        assert "₹" in content
        assert "€" in content

    def test_checksum_consistent(self, temp_dir):
        loader = DocumentLoader(temp_dir)
        path = Path(temp_dir, "doc1.md")

        checksum1 = loader.checksum(path)
        checksum2 = loader.checksum(path)
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 hex

    def test_checksum_differs_for_different_content(self, temp_dir):
        loader = DocumentLoader(temp_dir)

        checksum1 = loader.checksum(Path(temp_dir, "doc1.md"))
        checksum2 = loader.checksum(Path(temp_dir, "doc2.md"))
        assert checksum1 != checksum2

    def test_load_all(self, temp_dir):
        loader = DocumentLoader(temp_dir)
        results = loader.load_all()

        assert len(results) == 3
        for path, content, checksum in results:
            assert path.suffix == ".md"
            assert len(content) > 0
            assert len(checksum) == 64

    def test_nonexistent_directory_raises(self):
        with pytest.raises(FileNotFoundError):
            DocumentLoader("/nonexistent/path")

    def test_file_instead_of_directory_raises(self, temp_dir):
        file_path = Path(temp_dir, "doc1.md")
        with pytest.raises(NotADirectoryError):
            DocumentLoader(file_path)


class TestFactExtractor:
    """Tests for FactExtractor."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock = Mock()
        mock.extract_facts.return_value = {
            "facts": [
                {
                    "fact_id": "F001",
                    "category": "company_info",
                    "key": "company_name",
                    "value": "Test Corp",
                    "value_type": "text",
                    "raw_text": "Test Corp",
                    "confidence": 1.0,
                    "location": {
                        "section": "Header",
                        "table": None,
                        "row": None,
                        "column": None,
                    },
                },
                {
                    "fact_id": "F002",
                    "category": "capital_structure",
                    "key": "authorized_shares",
                    "value": 30000,
                    "value_type": "integer",
                    "raw_text": "30,000 equity shares",
                    "confidence": 0.95,
                    "unit": "shares",
                    "location": {
                        "section": "Section 7",
                        "table": "Capital Structure",
                    },
                },
            ],
            "document_type": "pas3_form",
            "document_date": "2019-05-15",
        }
        return mock

    def test_extract_from_document(self, mock_llm_client):
        extractor = FactExtractor(mock_llm_client)

        extraction = extractor.extract_from_document(
            content="Test document content",
            file_path=Path("/test/doc.md"),
            doc_id="DOC_001",
        )

        assert extraction.doc_id == "DOC_001"
        assert extraction.document_type == "pas3_form"
        assert extraction.document_date == "2019-05-15"
        assert len(extraction.facts) == 2
        assert extraction.error is None

    def test_extracted_facts_have_correct_data(self, mock_llm_client):
        extractor = FactExtractor(mock_llm_client)

        extraction = extractor.extract_from_document(
            content="Test content",
            file_path=Path("/test/doc.md"),
            doc_id="DOC_001",
        )

        fact1 = extraction.facts[0]
        assert fact1.fact_id == "F001"
        assert fact1.category == "company_info"
        assert fact1.key == "company_name"
        assert fact1.value == "Test Corp"
        assert fact1.doc_id == "DOC_001"

        fact2 = extraction.facts[1]
        assert fact2.unit == "shares"
        assert fact2.confidence == 0.95
        assert fact2.location.table == "Capital Structure"

    def test_extract_handles_llm_error(self, mock_llm_client):
        mock_llm_client.extract_facts.side_effect = Exception("API Error")
        extractor = FactExtractor(mock_llm_client)

        extraction = extractor.extract_from_document(
            content="Test content",
            file_path=Path("/test/doc.md"),
            doc_id="DOC_001",
        )

        assert extraction.document_type == "error"
        assert extraction.facts == []
        assert "API Error" in extraction.error

    def test_extract_all(self, mock_llm_client):
        extractor = FactExtractor(mock_llm_client)

        documents = [
            (Path("/test/doc1.md"), "Content 1", "checksum1"),
            (Path("/test/doc2.md"), "Content 2", "checksum2"),
        ]

        store = extractor.extract_all(documents)

        assert isinstance(store, FactStore)
        assert len(store.extractions) == 2
        assert store.extractions[0].doc_id == "DOC_001"
        assert store.extractions[1].doc_id == "DOC_002"

    def test_save_fact_store(self, mock_llm_client, tmp_path):
        extractor = FactExtractor(mock_llm_client)

        documents = [(Path("/test/doc1.md"), "Content 1", "checksum1")]
        store = extractor.extract_all(documents)

        output_path = tmp_path / "out" / "fact_store.json"
        extractor.save_fact_store(store, output_path)

        assert output_path.exists()

        # Verify JSON is valid
        data = json.loads(output_path.read_text())
        assert "extractions" in data
        assert len(data["extractions"]) == 1
        assert data["extractions"][0]["doc_id"] == "DOC_001"


class TestDocumentLoaderWithRealFiles:
    """Integration tests with real PAS-3 files."""

    @pytest.fixture
    def pas3_dir(self):
        """Return path to PAS-3 directory if it exists."""
        path = Path(__file__).parent.parent / "supporting_docs" / "PAS-3"
        if path.exists():
            return path
        pytest.skip("PAS-3 sample files not available")

    def test_load_pas3_files(self, pas3_dir):
        loader = DocumentLoader(pas3_dir)
        files = loader.discover()

        assert len(files) == 3
        file_names = {f.name for f in files}
        assert "Board Resolution Allotment of Shares.md" in file_names
        assert "List of Allottees.md" in file_names
        assert "PAS-3 Form.md" in file_names

    def test_read_pas3_content(self, pas3_dir):
        loader = DocumentLoader(pas3_dir)
        results = loader.load_all()

        for path, content, checksum in results:
            assert len(content) > 100  # Files have substantial content
            assert "Nexus" in content or "NEXUS" in content  # Company name appears
