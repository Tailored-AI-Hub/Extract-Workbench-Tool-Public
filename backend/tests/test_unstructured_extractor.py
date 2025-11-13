"""
Tests for Unstructured extractor using pytest.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.extractors.unstructured_extractor import UnstructuredExtractor


@pytest.fixture
def extractor():
    """Fixture for Unstructured extractor."""
    return UnstructuredExtractor()


def test_get_information(extractor):
    """Test that get_information returns correct information."""
    info = extractor.get_information()
    
    assert info['name'] == 'Unstructured'
    assert info['type'] == 'sync'
    assert 'text' in info['supports']
    assert 'tables' in info['supports']
    assert 'elements' in info['supports']
    assert 'Unstructured' in info['description']


def test_supports_webhook(extractor):
    """Test that Unstructured does not support webhooks."""
    assert not extractor.supports_webhook()


def test_get_status(extractor):
    """Test that get_status always returns 'succeeded' for sync extractor."""
    status = extractor.get_status("any_job_id")
    assert status == 'succeeded'


@patch('src.extractors.unstructured_extractor.partition_pdf')
def test_read_success(extractor, mock_partition_pdf):
    """Test successful PDF reading with Unstructured."""
    # Create mock elements
    mock_text_element = MagicMock()
    mock_text_element.__class__.__name__ = 'Text'
    mock_text_element.metadata = {'page_number': 1}
    mock_text_element.__str__ = MagicMock(return_value="This is text content.")
    
    mock_table_element = MagicMock()
    mock_table_element.__class__.__name__ = 'Table'
    mock_table_element.metadata = {'page_number': 1}
    mock_table_element.__str__ = MagicMock(return_value="| Col1 | Col2 |\n|------|------|\n| A    | B    |")
    
    mock_title_element = MagicMock()
    mock_title_element.__class__.__name__ = 'Title'
    mock_title_element.metadata = {'page_number': 1}
    mock_title_element.__str__ = MagicMock(return_value="Document Title")
    
    mock_elements = [mock_text_element, mock_table_element, mock_title_element]
    mock_partition_pdf.return_value = mock_elements
    
    # Test the extraction
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
    assert 'TEXT' in content
    assert 'TABLES' in content
    assert 'ELEMENTS' in content
    
    # Check that text content includes all text elements
    text_content = content['TEXT']
    assert 'This is text content.' in text_content
    assert 'Document Title' in text_content
    
    # Check that table content includes table elements
    table_content = content['TABLES']
    assert '| Col1 | Col2 |' in table_content
    
    # Check that elements list includes all elements
    elements = content['ELEMENTS']
    assert len(elements) == 3
    
    metadata = page_data['metadata']
    assert metadata['extractor'] == 'Unstructured'
    assert 'element_types' in metadata
    assert 'total_elements' in metadata
    assert 'tables_found' in metadata
    
    # Check element types
    element_types = metadata['element_types']
    assert 'Text' in element_types
    assert 'Table' in element_types
    assert 'Title' in element_types
    
    # Check counts
    assert metadata['total_elements'] == 3
    assert metadata['tables_found'] == 1


@patch('src.extractors.unstructured_extractor.partition_pdf')
def test_read_multiple_pages(extractor, mock_partition_pdf):
    """Test PDF reading with multiple pages."""
    # Create mock elements for multiple pages
    mock_page1_text = MagicMock()
    mock_page1_text.__class__.__name__ = 'Text'
    mock_page1_text.metadata = {'page_number': 1}
    mock_page1_text.__str__ = MagicMock(return_value="Page 1 content")
    
    mock_page2_text = MagicMock()
    mock_page2_text.__class__.__name__ = 'Text'
    mock_page2_text.metadata = {'page_number': 2}
    mock_page2_text.__str__ = MagicMock(return_value="Page 2 content")
    
    mock_page2_table = MagicMock()
    mock_page2_table.__class__.__name__ = 'Table'
    mock_page2_table.metadata = {'page_number': 2}
    mock_page2_table.__str__ = MagicMock(return_value="| Page 2 Table |")
    
    mock_elements = [mock_page1_text, mock_page2_text, mock_page2_table]
    mock_partition_pdf.return_value = mock_elements
    
    # Test the extraction
    result = extractor.read("test.pdf")
    
    # Verify the result
    assert result is True
    stored_result = extractor._last_result
    
    # Should have both pages
    assert 1 in stored_result
    assert 2 in stored_result
    
    # Check page 1
    page1_data = stored_result[1]
    assert 'Page 1 content' in page1_data['content']['TEXT']
    assert page1_data['metadata']['total_elements'] == 1
    assert page1_data['metadata']['tables_found'] == 0
    
    # Check page 2
    page2_data = stored_result[2]
    assert 'Page 2 content' in page2_data['content']['TEXT']
    assert '| Page 2 Table |' in page2_data['content']['TABLES']
    assert page2_data['metadata']['total_elements'] == 2
    assert page2_data['metadata']['tables_found'] == 1


@patch('src.extractors.unstructured_extractor.partition_pdf')
def test_read_failure(extractor, mock_partition_pdf):
    """Test PDF reading failure with Unstructured."""
    # Mock the partition_pdf function to raise an exception
    mock_partition_pdf.side_effect = Exception("Unstructured error")
    
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
    assert content['TEXT'] == ''
    assert content['TABLES'] == ''
    assert content['ELEMENTS'] == []
    
    # Metadata should contain error info
    metadata = page_data['metadata']
    assert 'error' in metadata
    assert metadata['error'] == 'Unstructured error'


def test_get_result(extractor):
    """Test that get_result returns the last extraction result."""
    # Set up a mock result
    mock_result = {
        1: {
            'content': {
                'TEXT': 'Test text',
                'TABLES': 'Test table',
                'ELEMENTS': ['element1', 'element2']
            },
            'metadata': {
                'extractor': 'Unstructured',
                'element_types': ['Text', 'Table'],
                'total_elements': 2,
                'tables_found': 1
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


@patch('src.extractors.unstructured_extractor.partition_pdf')
def test_extraction_workflow_with_mock(extractor, mock_partition_pdf):
    """Test the complete extraction workflow with mocked Unstructured."""
    # Mock successful extraction
    mock_text_element = MagicMock()
    mock_text_element.__class__.__name__ = 'Text'
    mock_text_element.metadata = {'page_number': 1}
    mock_text_element.__str__ = MagicMock(return_value="Test content")
    
    mock_table_element = MagicMock()
    mock_table_element.__class__.__name__ = 'Table'
    mock_table_element.metadata = {'page_number': 1}
    mock_table_element.__str__ = MagicMock(return_value="| A | B |")
    
    mock_elements = [mock_text_element, mock_table_element]
    mock_partition_pdf.return_value = mock_elements
    
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
    assert 'TEXT' in content
    assert 'TABLES' in content
    assert 'ELEMENTS' in content
    assert 'Test content' in content['TEXT']
    assert '| A | B |' in content['TABLES']
    
    metadata = page_data['metadata']
    assert metadata['extractor'] == 'Unstructured'
    assert 'Text' in metadata['element_types']
    assert 'Table' in metadata['element_types']
    assert metadata['total_elements'] == 2
    assert metadata['tables_found'] == 1


# Parametrized test for different element types
@pytest.mark.parametrize("element_type,expected_in_text", [
    ('Text', True),
    ('Title', True),
    ('Table', False),  # Tables go to separate field
    ('Header', True),
    ('Footer', True),
])
@patch('src.extractors.unstructured_extractor.partition_pdf')
def test_different_element_types(extractor, mock_partition_pdf, element_type, expected_in_text):
    """Test handling of different element types."""
    mock_element = MagicMock()
    mock_element.__class__.__name__ = element_type
    mock_element.metadata = {'page_number': 1}
    mock_element.__str__ = MagicMock(return_value=f"{element_type} content")
    
    mock_partition_pdf.return_value = [mock_element]
    
    result = extractor.read("test.pdf")
    assert result is True
    
    stored_result = extractor._last_result
    page_data = stored_result[1]
    content = page_data['content']
    
    if expected_in_text:
        assert f"{element_type} content" in content['TEXT']
    else:
        assert f"{element_type} content" in content['TABLES']


if __name__ == '__main__':
    # Example usage with a real PDF file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            print(f"Running Unstructured tests with file: {test_file}")
            
            # Run specific tests with real file
            extractor = UnstructuredExtractor()
            
            # Test read with real file
            result = extractor.read(test_file)
            print(f"Read result: {result}")
            
            # Test extraction workflow
            status = extractor.get_status("test_job_id")
            print(f"Status: {status}")
            
            extraction_result = extractor.get_result("test_job_id")
            print(f"Extraction result: {extraction_result}")
            
            print("Unstructured extractor tests completed!")
        else:
            print(f"File not found: {test_file}")
    else:
        # Run all tests with mocks
        pytest.main([__file__])
