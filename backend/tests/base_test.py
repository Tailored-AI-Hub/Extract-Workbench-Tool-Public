"""
Base test utilities and fixtures for PDF extractors.
Provides common test utilities and setup using pytest.
"""
import os
import sys
import pytest
from pathlib import Path
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.interface import PDFExtractorInterface


@pytest.fixture
def test_pdf_path():
    """Fixture for test PDF file path."""
    return None


@pytest.fixture
def extractor():
    """Fixture for extractor instance - to be overridden in specific tests."""
    return None


def test_extractor_interface(extractor):
    """Test that the extractor implements the required interface."""
    assert extractor is not None, "Extractor instance not set"
    
    # Test that all required methods exist
    assert hasattr(extractor, 'get_information')
    assert hasattr(extractor, 'read')
    assert hasattr(extractor, 'get_status')
    assert hasattr(extractor, 'get_result')
    assert hasattr(extractor, 'supports_webhook')
    assert hasattr(extractor, 'handle_webhook')


def test_get_information(extractor):
    """Test that get_information returns a valid dict."""
    info = extractor.get_information()
    assert isinstance(info, dict), "get_information should return a dict"
    
    required_keys = ['name', 'type', 'supports', 'description']
    for key in required_keys:
        assert key in info, f"get_information should contain '{key}'"


def test_read_without_file(extractor):
    """Test that read raises appropriate error without file."""
    with pytest.raises((FileNotFoundError, TypeError, ValueError)):
        extractor.read("nonexistent_file.pdf")


def test_read_with_file(extractor, test_pdf_path):
    """Test that read works with a valid file."""
    if not test_pdf_path:
        pytest.skip("No test file provided")
        
    result = extractor.read(test_pdf_path)
    assert result is not None, "read should return a result"


def test_get_status(extractor):
    """Test that get_status returns a valid status."""
    status = extractor.get_status("test_job_id")
    valid_statuses = ['pending', 'running', 'succeeded', 'failed']
    assert status in valid_statuses, f"Invalid status: {status}"


def test_get_result(extractor):
    """Test that get_result returns a valid result."""
    result = extractor.get_result("test_job_id")
    assert result is not None, "get_result should return a result"


def test_supports_webhook(extractor):
    """Test that supports_webhook returns a boolean."""
    supports = extractor.supports_webhook()
    assert isinstance(supports, bool), "supports_webhook should return a boolean"


def test_handle_webhook(extractor):
    """Test that handle_webhook handles webhook payloads."""
    test_payload = {"test": "data"}
    
    if extractor.supports_webhook():
        # If webhook is supported, it should handle the payload
        result = extractor.handle_webhook(test_payload)
        assert result is not None, "handle_webhook should return a result"
    else:
        # If webhook is not supported, it should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            extractor.handle_webhook(test_payload)


def test_extraction_workflow(extractor, test_pdf_path):
    """Test the complete extraction workflow."""
    if not test_pdf_path:
        pytest.skip("No test file provided")
        
    # Test read
    result = extractor.read(test_pdf_path)
    assert result is not None, "read should return a result"
    
    # Test get_status
    status = extractor.get_status("test_job_id")
    assert status in ['pending', 'running', 'succeeded', 'failed']
    
    # Test get_result
    extraction_result = extractor.get_result("test_job_id")
    assert extraction_result is not None, "get_result should return extraction data"
    
    # If it's a dict, check structure
    if isinstance(extraction_result, dict):
        assert len(extraction_result) > 0, "Extraction result should not be empty"
        
        # Check that each page has content
        for page_num, page_data in extraction_result.items():
            assert isinstance(page_num, int), "Page numbers should be integers"
            assert isinstance(page_data, dict), "Page data should be a dict"
            
            if 'content' in page_data:
                assert isinstance(page_data['content'], dict), "Content should be a dict"
                assert len(page_data['content']) > 0, "Content should not be empty"
