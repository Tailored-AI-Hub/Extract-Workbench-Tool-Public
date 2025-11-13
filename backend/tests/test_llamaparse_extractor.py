"""
Tests for LlamaParse extractor using pytest.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.extractors.llamaparse import LlamaParseExtractor


@pytest.fixture
def extractor():
    """Fixture for LlamaParse extractor."""
    return LlamaParseExtractor()


def test_get_information(extractor):
    """Test that get_information returns correct information."""
    info = extractor.get_information()
    
    assert info['name'] == 'LlamaParse'
    assert info['type'] == 'async'
    assert 'text' in info['supports']
    assert 'tables' in info['supports']
    assert 'markdown' in info['supports']
    assert 'LlamaParse' in info['description']


def test_supports_webhook(extractor):
    """Test that LlamaParse supports webhooks."""
    assert extractor.supports_webhook()


@patch('src.extractors.llamaparse.requests.post')
def test_read_success(extractor, mock_post):
    """Test successful job creation with LlamaParse."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {'id': 'test_job_123'}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    # Mock file reading
    with patch('builtins.open', mock_open(read_data=b'PDF content')):
        result = extractor.read('test.pdf')
        
    # Verify the result
    assert result == 'test_job_123'
    assert extractor._job_id == 'test_job_123'
    
    # Verify API call
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert 'upload_url' in call_args[0][0]
    assert 'files' in call_args[1]


@patch('src.extractors.llamaparse.requests.post')
def test_read_failure(extractor, mock_post):
    """Test job creation failure with LlamaParse."""
    # Mock API failure
    mock_post.side_effect = Exception("API Error")
    
    with patch('builtins.open', mock_open(read_data=b'PDF content')):
        with pytest.raises(Exception):
            extractor.read('test.pdf')


@pytest.mark.parametrize("status,expected", [
    ('SUCCESS', 'succeeded'),
    ('FAILED', 'failed'),
    ('RUNNING', 'running'),
    ('PENDING', 'pending')
])
@patch('src.extractors.llamaparse.requests.get')
def test_get_status_success(extractor, mock_get, status, expected):
    """Test successful status check with LlamaParse."""
    # Mock successful status response
    mock_response = MagicMock()
    mock_response.json.return_value = {'status': status}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    result_status = extractor.get_status('test_job_123')
    assert result_status == expected


@patch('src.extractors.llamaparse.requests.get')
def test_get_status_failure(extractor, mock_get):
    """Test status check failure with LlamaParse."""
    # Mock API failure
    mock_get.side_effect = Exception("API Error")
    
    status = extractor.get_status('test_job_123')
    assert status == 'failed'


def test_get_status_no_job_id(extractor):
    """Test status check with no job ID."""
    status = extractor.get_status(None)
    assert status == 'failed'


@patch('src.extractors.llamaparse.requests.get')
def test_get_result_success(extractor, mock_get):
    """Test successful result retrieval with LlamaParse."""
    # Mock successful result response
    mock_response = MagicMock()
    mock_response.text = "# Test Document\n\nThis is the extracted content."
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    result = extractor.get_result('test_job_123')
    
    # Verify the result structure
    assert isinstance(result, dict)
    assert 1 in result
    
    page_data = result[1]
    assert 'content' in page_data
    assert 'metadata' in page_data
    
    content = page_data['content']
    assert 'MARKDOWN' in content
    assert 'TEXT' in content
    assert 'Test Document' in content['MARKDOWN']
    
    metadata = page_data['metadata']
    assert metadata['extractor'] == 'LlamaParse'
    assert metadata['format'] == 'markdown'
    assert metadata['job_id'] == 'test_job_123'


@patch('src.extractors.llamaparse.requests.get')
def test_get_result_failure(extractor, mock_get):
    """Test result retrieval failure with LlamaParse."""
    # Mock API failure
    mock_get.side_effect = Exception("API Error")
    
    result = extractor.get_result('test_job_123')
    assert result == {}


def test_get_result_no_job_id(extractor):
    """Test result retrieval with no job ID."""
    result = extractor.get_result(None)
    assert result == {}


@pytest.mark.parametrize("payload,expected_result", [
    ({'job_id': 'test_job_123', 'status': 'SUCCESS'}, {'test': 'result'}),
    ({'job_id': 'test_job_123', 'status': 'FAILED'}, {}),
    ({'status': 'SUCCESS'}, {}),
])
def test_handle_webhook(extractor, payload, expected_result):
    """Test webhook handling with different payloads."""
    with patch.object(extractor, 'get_result') as mock_get_result:
        mock_get_result.return_value = {'test': 'result'}
        
        result = extractor.handle_webhook(payload)
        assert result == expected_result


def test_handle_webhook_exception(extractor):
    """Test webhook handling with exception."""
    payload = {
        'job_id': 'test_job_123',
        'status': 'SUCCESS'
    }
    
    with patch.object(extractor, 'get_result') as mock_get_result:
        mock_get_result.side_effect = Exception("API Error")
        
        result = extractor.handle_webhook(payload)
        assert result == {}


@patch('src.extractors.llamaparse.requests.post')
@patch('src.extractors.llamaparse.requests.get')
def test_complete_workflow(extractor, mock_get, mock_post):
    """Test the complete async workflow."""
    # Mock job creation
    mock_post_response = MagicMock()
    mock_post_response.json.return_value = {'id': 'test_job_123'}
    mock_post_response.raise_for_status.return_value = None
    mock_post.return_value = mock_post_response
    
    # Mock status check
    mock_get_response = MagicMock()
    mock_get_response.json.return_value = {'status': 'SUCCESS'}
    mock_get_response.text = "# Test Document\n\nContent here."
    mock_get_response.raise_for_status.return_value = None
    mock_get.return_value = mock_get_response
    
    with patch('builtins.open', mock_open(read_data=b'PDF content')):
        # Test read (job creation)
        job_id = extractor.read('test.pdf')
        assert job_id == 'test_job_123'
        
        # Test get_status
        status = extractor.get_status(job_id)
        assert status == 'succeeded'
        
        # Test get_result
        result = extractor.get_result(job_id)
        assert isinstance(result, dict)
        assert 1 in result
        
        # Verify content
        page_data = result[1]
        content = page_data['content']
        assert 'Test Document' in content['MARKDOWN']


# Test with different job IDs
@pytest.mark.parametrize("job_id", ["job_123", "test_job", "abc_xyz"])
def test_get_status_with_different_job_ids(extractor, job_id):
    """Test get_status with different job IDs."""
    with patch('src.extractors.llamaparse.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {'status': 'SUCCESS'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        status = extractor.get_status(job_id)
        assert status == 'succeeded'


if __name__ == '__main__':
    # Example usage with a real PDF file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            print(f"Running LlamaParse tests with file: {test_file}")
            print("Note: LlamaParse requires API key and network access")
            
            # Run specific tests with real file (these will fail without API key)
            extractor = LlamaParseExtractor()
            
            try:
                # Test read with real file
                result = extractor.read(test_file)
                print(f"Read result: {result}")
                
                # Test extraction workflow
                status = extractor.get_status("test_job_id")
                print(f"Status: {status}")
                
                extraction_result = extractor.get_result("test_job_id")
                print(f"Extraction result: {extraction_result}")
                
            except Exception as e:
                print(f"LlamaParse tests failed (expected without API key): {e}")
            
            print("LlamaParse extractor tests completed!")
        else:
            print(f"File not found: {test_file}")
    else:
        # Run all tests with mocks
        pytest.main([__file__])
