"""
Tests for MarkItDown extractor using pytest.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.extractors.markitdown_extractor import MarkItDownExtractor


@pytest.fixture
def extractor():
    """Fixture for MarkItDown extractor."""
    return MarkItDownExtractor()


def test_get_information(extractor):
    """Test that get_information returns correct information."""
    info = extractor.get_information()
    
    assert info['name'] == 'MarkItDown'
    assert info['type'] == 'sync'
    assert 'text' in info['supports']
    assert 'tables' in info['supports']
    assert 'markdown' in info['supports']
    assert 'MarkItDown' in info['description']


def test_supports_webhook(extractor):
    """Test that MarkItDown does not support webhooks."""
    assert not extractor.supports_webhook()


def test_get_status(extractor):
    """Test that get_status always returns 'succeeded' for sync extractor."""
    status = extractor.get_status("any_job_id")
    assert status == 'succeeded'


@patch('src.extractors.markitdown_extractor.markitdown')
def test_read_success(extractor, mock_markitdown):
    """Test successful PDF reading with MarkItDown."""
    # Mock the markitdown.convert function
    mock_result = MagicMock()
    mock_result.text_content = "# Test Document\n\nThis is test content."
    mock_markitdown.convert.return_value = mock_result
    
    # Use a dummy file path since we're mocking
    test_file = "test.pdf"
    result = extractor.read(test_file)
    
    # Verify the result
    assert result is True  # Should return True for sync extractors
    assert extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = extractor._last_result
    assert 1 in stored_result  # Should have page 1
    page_data = stored_result[1]
    
    assert 'content' in page_data
    assert 'metadata' in page_data
    
    content = page_data['content']
    assert 'MARKDOWN' in content
    assert 'TEXT' in content
    assert content['MARKDOWN'] == "# Test Document\n\nThis is test content."
    assert content['TEXT'] == "# Test Document\n\nThis is test content."
    
    metadata = page_data['metadata']
    assert metadata['extractor'] == 'MarkItDown'
    assert metadata['format'] == 'markdown'


@patch('src.extractors.markitdown_extractor.markitdown')
def test_read_failure(extractor, mock_markitdown):
    """Test PDF reading failure with MarkItDown."""
    # Mock the markitdown.convert function to raise an exception
    mock_markitdown.convert.side_effect = Exception("MarkItDown error")
    
    test_file = "test.pdf"
    result = extractor.read(test_file)
    
    # Should still return True even on error (sync extractor pattern)
    assert result is True
    assert extractor._last_result is not None
    
    # Check error handling
    stored_result = extractor._last_result
    assert 1 in stored_result
    page_data = stored_result[1]
    
    assert 'content' in page_data
    assert 'metadata' in page_data
    
    # Content should be empty on error
    content = page_data['content']
    assert content['MARKDOWN'] == ''
    assert content['TEXT'] == ''
    
    # Metadata should contain error info
    metadata = page_data['metadata']
    assert 'error' in metadata
    assert metadata['error'] == 'MarkItDown error'


def test_get_result(extractor):
    """Test that get_result returns the last extraction result."""
    # Set up a mock result
    mock_result = {
        1: {
            'content': {
                'MARKDOWN': '# Test',
                'TEXT': '# Test'
            },
            'metadata': {
                'extractor': 'MarkItDown'
            }
        }
    }
    extractor._last_result = mock_result
    
    result = extractor.get_result("any_job_id")
    assert result == mock_result


def test_handle_webhook(extractor):
    """Test that handle_webhook raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        extractor.handle_webhook({"test": "data"})


@patch('src.extractors.markitdown_extractor.markitdown')
def test_extraction_workflow_with_mock(extractor, mock_markitdown):
    """Test the complete extraction workflow with mocked MarkItDown."""
    # Mock successful conversion
    mock_result = MagicMock()
    mock_result.text_content = "# Test Document\n\nContent here."
    mock_markitdown.convert.return_value = mock_result
    
    # Test read
    result = extractor.read("test.pdf")
    assert result is True
    
    # Test get_status
    status = extractor.get_status("test_job_id")
    assert status == 'succeeded'
    
    # Test get_result
    extraction_result = extractor.get_result("test_job_id")
    assert extraction_result is not None
    assert isinstance(extraction_result, dict)
    assert 1 in extraction_result
    
    # Verify content structure
    page_data = extraction_result[1]
    assert 'content' in page_data
    assert 'metadata' in page_data
    
    content = page_data['content']
    assert 'MARKDOWN' in content
    assert 'TEXT' in content
    assert 'Test Document' in content['MARKDOWN']


# Parametrized test for different file types
@pytest.mark.parametrize("file_path", ["test.pdf", "document.pdf", "sample.pdf"])
@patch('src.extractors.markitdown_extractor.markitdown')
def test_read_with_different_files(extractor, mock_markitdown, file_path):
    """Test reading with different file paths."""
    mock_result = MagicMock()
    mock_result.text_content = f"Content from {file_path}"
    mock_markitdown.convert.return_value = mock_result
    
    result = extractor.read(file_path)
    assert result is True
    assert extractor._last_result is not None


if __name__ == '__main__':
    # Example usage with a real PDF file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            print(f"Running MarkItDown tests with file: {test_file}")
            
            # Run specific tests with real file
            extractor = MarkItDownExtractor()
            
            # Test read with real file
            result = extractor.read(test_file)
            print(f"Read result: {result}")
            
            # Test extraction workflow
            status = extractor.get_status("test_job_id")
            print(f"Status: {status}")
            
            extraction_result = extractor.get_result("test_job_id")
            print(f"Extraction result: {extraction_result}")
            
            print("MarkItDown extractor tests completed!")
        else:
            print(f"File not found: {test_file}")
    else:
        # Run all tests with mocks
        pytest.main([__file__])
