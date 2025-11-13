"""
Pytest configuration and shared fixtures for PDF extractor tests.
"""
import os
import sys
import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def test_pdf_path():
    """Session-scoped fixture for test PDF file path."""
    # This can be overridden by command line arguments or environment variables
    return os.getenv('TEST_PDF_PATH', None)


@pytest.fixture
def markitdown_extractor():
    """Fixture for MarkItDown extractor."""
    from src.extractors.markitdown_extractor import MarkItDownExtractor
    return MarkItDownExtractor()


@pytest.fixture
def llamaparse_extractor():
    """Fixture for LlamaParse extractor."""
    from src.extractors.llamaparse import LlamaParseExtractor
    return LlamaParseExtractor()


@pytest.fixture
def unstructured_extractor():
    """Fixture for Unstructured extractor."""
    from src.extractors.unstructured_extractor import UnstructuredExtractor
    return UnstructuredExtractor()


@pytest.fixture
def pypdf2_extractor():
    """Fixture for PyPDF2 extractor."""
    from src.extractors.pypdf2_extractor import PyPDF2Extractor
    return PyPDF2Extractor()


@pytest.fixture
def pymupdf_extractor():
    """Fixture for PyMuPDF extractor."""
    from src.extractors.pymupdf_extractor import PyMuPDFExtractor
    return PyMuPDFExtractor()


@pytest.fixture
def pdfplumber_extractor():
    """Fixture for PDFPlumber extractor."""
    from src.extractors.pdfplumber_extractor import PDFPlumberExtractor
    return PDFPlumberExtractor()


@pytest.fixture
def camelot_extractor():
    """Fixture for Camelot extractor."""
    from src.extractors.camelot_extractor import CamelotExtractor
    return CamelotExtractor()


@pytest.fixture
def tesseract_extractor():
    """Fixture for Tesseract extractor."""
    from src.extractors.tesseract_extractor import TesseractExtractor
    return TesseractExtractor()


# Parametrized fixture for all extractors
@pytest.fixture(params=[
    'markitdown_extractor',
    'llamaparse_extractor', 
    'unstructured_extractor',
    'pypdf2_extractor',
    'pymupdf_extractor',
    'pdfplumber_extractor',
    'camelot_extractor',
    'tesseract_extractor'
])
def any_extractor(request):
    """Parametrized fixture that provides any extractor."""
    return request.getfixturevalue(request.param)


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "mock: mark test as using mocked dependencies")
    config.addinivalue_line("markers", "real_file: mark test as requiring a real PDF file")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


# Command line options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--pdf-file", 
        action="store", 
        default=None,
        help="Path to PDF file for real file testing"
    )
    parser.addoption(
        "--mock-only", 
        action="store_true", 
        default=False,
        help="Run only mock tests"
    )
    parser.addoption(
        "--real-only", 
        action="store_true", 
        default=False,
        help="Run only real file tests"
    )


# Skip real file tests if no file provided
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    pdf_file = config.getoption("--pdf-file")
    mock_only = config.getoption("--mock-only")
    real_only = config.getoption("--real-only")
    
    if mock_only:
        # Skip real file tests
        for item in items:
            if "real_file" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Mock only mode"))
    elif real_only:
        # Skip mock tests
        for item in items:
            if "mock" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Real file only mode"))
    elif not pdf_file:
        # Skip real file tests if no file provided
        for item in items:
            if "real_file" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="No PDF file provided"))
