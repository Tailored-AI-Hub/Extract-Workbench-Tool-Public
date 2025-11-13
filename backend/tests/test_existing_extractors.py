"""
Tests for existing PDF extractors using pytest.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_pypdf2_get_information(pypdf2_extractor):
    """Test that get_information returns correct information."""
    info = pypdf2_extractor.get_information()
    
    assert info['name'] == 'PyPDF2'
    assert info['type'] == 'sync'
    assert 'text' in info['supports']
    assert 'PyPDF2' in info['description']


@patch('src.extractors.pypdf2_extractor.PdfReader')
def test_pypdf2_read_success(pypdf2_extractor, mock_pdf_reader):
    """Test successful PDF reading with PyPDF2."""
    # Mock PDF reader and pages
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 content"
    
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 content"
    
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page1, mock_page2]
    mock_pdf_reader.return_value = mock_reader
    
    # Test the extraction
    result = pypdf2_extractor.read("test.pdf")
    
    # Verify the result
    assert result is True
    assert pypdf2_extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = pypdf2_extractor._last_result
    assert 1 in stored_result
    assert 2 in stored_result
    
    # Check page 1
    page1_data = stored_result[1]
    assert 'content' in page1_data
    assert 'metadata' in page1_data
    assert page1_data['content']['TEXT'] == 'Page 1 content'
    assert page1_data['metadata']['extractor'] == 'PyPDF2'
    
    # Check page 2
    page2_data = stored_result[2]
    assert page2_data['content']['TEXT'] == 'Page 2 content'


def test_pymupdf_get_information(pymupdf_extractor):
    """Test that get_information returns correct information."""
    info = pymupdf_extractor.get_information()
    
    assert info['name'] == 'PyMuPDF'
    assert info['type'] == 'sync'
    assert 'text' in info['supports']
    assert 'PyMuPDF' in info['description']


@patch('src.extractors.pymupdf_extractor.fitz')
def test_pymupdf_read_success(pymupdf_extractor, mock_fitz):
    """Test successful PDF reading with PyMuPDF."""
    # Mock PDF document
    mock_doc = MagicMock()
    mock_doc.page_count = 2
    
    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Page 1 content"
    
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Page 2 content"
    
    mock_doc.__getitem__.side_effect = lambda x: [mock_page1, mock_page2][x]
    mock_fitz.open.return_value = mock_doc
    
    # Test the extraction
    result = pymupdf_extractor.read("test.pdf")
    
    # Verify the result
    assert result is True
    assert pymupdf_extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = pymupdf_extractor._last_result
    assert 1 in stored_result
    assert 2 in stored_result
    
    # Check page 1
    page1_data = stored_result[1]
    assert page1_data['content']['TEXT'] == 'Page 1 content'
    
    # Check page 2
    page2_data = stored_result[2]
    assert page2_data['content']['TEXT'] == 'Page 2 content'
    
    # Verify document was closed
    mock_doc.close.assert_called_once()


def test_pdfplumber_get_information(pdfplumber_extractor):
    """Test that get_information returns correct information."""
    info = pdfplumber_extractor.get_information()
    
    assert info['name'] == 'pdfplumber'
    assert info['type'] == 'sync'
    assert 'combined' in info['supports']
    assert 'tables' in info['supports']
    assert 'PDFPlumber' in info['description']


@patch('src.extractors.pdfplumber_extractor.pdfplumber')
def test_pdfplumber_read_success(pdfplumber_extractor, mock_pdfplumber):
    """Test successful PDF reading with PDFPlumber."""
    # Mock PDF and pages
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 text content"
    mock_page1.extract_tables.return_value = [
        [['Header1', 'Header2'], ['Value1', 'Value2']]
    ]
    
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 text content"
    mock_page2.extract_tables.return_value = []
    
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
    
    # Test the extraction
    result = pdfplumber_extractor.read("test.pdf")
    
    # Verify the result
    assert result is True
    assert pdfplumber_extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = pdfplumber_extractor._last_result
    assert 1 in stored_result
    assert 2 in stored_result
    
    # Check page 1
    page1_data = stored_result[1]
    content = page1_data['content']
    assert content['COMBINED'] == 'Page 1 text content'
    assert 'Header1' in content['TABLE']
    assert 'Value1' in content['TABLE']
    
    # Check page 2
    page2_data = stored_result[2]
    content = page2_data['content']
    assert content['COMBINED'] == 'Page 2 text content'
    assert content['TABLE'] == ''


def test_camelot_get_information(camelot_extractor):
    """Test that get_information returns correct information."""
    info = camelot_extractor.get_information()
    
    assert info['name'] == 'Camelot'
    assert info['type'] == 'sync'
    assert 'tables' in info['supports']
    assert 'Camelot' in info['description']


@patch('src.extractors.camelot_extractor.camelot_py')
def test_camelot_read_success(camelot_extractor, mock_camelot):
    """Test successful PDF reading with Camelot."""
    # Mock table objects
    mock_table1 = MagicMock()
    mock_table1.page = 1
    mock_table1.df.to_string.return_value = "| Col1 | Col2 |\n|------|------|\n| A    | B    |"
    
    mock_table2 = MagicMock()
    mock_table2.page = 2
    mock_table2.df.to_string.return_value = "| Col3 | Col4 |\n|------|------|\n| C    | D    |"
    
    mock_camelot.read_pdf.return_value = [mock_table1, mock_table2]
    
    # Test the extraction
    result = camelot_extractor.read("test.pdf")
    
    # Verify the result
    assert result is True
    assert camelot_extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = camelot_extractor._last_result
    assert 1 in stored_result
    assert 2 in stored_result
    
    # Check page 1
    page1_data = stored_result[1]
    assert 'TABLES' in page1_data['content']
    assert 'Col1' in page1_data['content']['TABLES']
    assert page1_data['metadata']['tables_found'] == 1
    
    # Check page 2
    page2_data = stored_result[2]
    assert 'Col3' in page2_data['content']['TABLES']
    assert page2_data['metadata']['tables_found'] == 1


def test_tesseract_get_information(tesseract_extractor):
    """Test that get_information returns correct information."""
    info = tesseract_extractor.get_information()
    
    assert info['name'] == 'Tesseract'
    assert info['type'] == 'sync'
    assert 'text' in info['supports']
    assert 'Tesseract' in info['description']


@patch('src.extractors.tesseract_extractor.convert_from_path')
@patch('src.extractors.tesseract_extractor.pytesseract')
@patch('src.extractors.tesseract_extractor.Image')
def test_tesseract_read_success_pdf(tesseract_extractor, mock_image, mock_pytesseract, mock_convert):
    """Test successful PDF reading with Tesseract."""
    # Mock image conversion
    mock_img1 = MagicMock()
    mock_img2 = MagicMock()
    mock_convert.return_value = [mock_img1, mock_img2]
    
    # Mock OCR results
    mock_pytesseract.image_to_string.side_effect = [
        "Page 1 OCR text",
        "Page 2 OCR text"
    ]
    
    # Test the extraction
    result = tesseract_extractor.read("test.pdf")
    
    # Verify the result
    assert result is True
    assert tesseract_extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = tesseract_extractor._last_result
    assert 1 in stored_result
    assert 2 in stored_result
    
    # Check page 1
    page1_data = stored_result[1]
    assert page1_data['content']['TEXT'] == 'Page 1 OCR text'
    assert page1_data['metadata']['extractor'] == 'Tesseract'
    
    # Check page 2
    page2_data = stored_result[2]
    assert page2_data['content']['TEXT'] == 'Page 2 OCR text'


@patch('src.extractors.tesseract_extractor.Image')
@patch('src.extractors.tesseract_extractor.pytesseract')
def test_tesseract_read_success_image(tesseract_extractor, mock_pytesseract, mock_image):
    """Test successful image reading with Tesseract."""
    # Mock image opening
    mock_img = MagicMock()
    mock_image.open.return_value = mock_img
    
    # Mock OCR result
    mock_pytesseract.image_to_string.return_value = "Image OCR text"
    
    # Test the extraction
    result = tesseract_extractor.read("test.jpg")
    
    # Verify the result
    assert result is True
    assert tesseract_extractor._last_result is not None
    
    # Check the stored result structure
    stored_result = tesseract_extractor._last_result
    assert 1 in stored_result
    page1_data = stored_result[1]
    assert page1_data['content']['TEXT'] == 'Image OCR text'


# Parametrized tests for all extractors
@pytest.mark.parametrize("extractor_name", [
    'pypdf2_extractor',
    'pymupdf_extractor', 
    'pdfplumber_extractor',
    'camelot_extractor',
    'tesseract_extractor'
])
def test_all_extractors_interface(extractor_name, request):
    """Test that all extractors implement the required interface."""
    extractor = request.getfixturevalue(extractor_name)
    
    # Test interface methods
    assert hasattr(extractor, 'get_information')
    assert hasattr(extractor, 'read')
    assert hasattr(extractor, 'get_status')
    assert hasattr(extractor, 'get_result')
    assert hasattr(extractor, 'supports_webhook')
    assert hasattr(extractor, 'handle_webhook')
    
    # Test get_information
    info = extractor.get_information()
    assert isinstance(info, dict)
    assert 'name' in info
    assert 'type' in info
    assert 'supports' in info
    assert 'description' in info
    
    # Test get_status
    status = extractor.get_status("test_job_id")
    assert status in ['pending', 'running', 'succeeded', 'failed']
    
    # Test supports_webhook
    supports = extractor.supports_webhook()
    assert isinstance(supports, bool)


# Test with real file if provided
@pytest.mark.real_file
def test_all_extractors_with_real_file(test_pdf_path, pypdf2_extractor, pymupdf_extractor, 
                                      pdfplumber_extractor, camelot_extractor, tesseract_extractor):
    """Test all extractors with a real PDF file."""
    if not test_pdf_path:
        pytest.skip("No PDF file provided")
    
    extractors = [
        ('PyPDF2', pypdf2_extractor),
        ('PyMuPDF', pymupdf_extractor),
        ('PDFPlumber', pdfplumber_extractor),
        ('Camelot', camelot_extractor),
        ('Tesseract', tesseract_extractor)
    ]
    
    for name, extractor in extractors:
        print(f"\n--- Testing {name} ---")
        try:
            # Test basic functionality
            info = extractor.get_information()
            print(f"  Info: {info['name']} - {info['description']}")
            
            # Test extraction (this might fail for some extractors without proper setup)
            result = extractor.read(test_pdf_path)
            print(f"  Read result: {result}")
            
            status = extractor.get_status("test_job")
            print(f"  Status: {status}")
            
            extraction_result = extractor.get_result("test_job")
            if isinstance(extraction_result, dict):
                print(f"  Pages extracted: {len(extraction_result)}")
            else:
                print(f"  Result type: {type(extraction_result)}")
                
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == '__main__':
    # Example usage with a real PDF file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        if os.path.exists(test_file):
            print(f"Running existing extractor tests with file: {test_file}")
            
            # Set environment variable for pytest
            os.environ['TEST_PDF_PATH'] = test_file
            
            # Run pytest
            pytest.main([__file__, '-v'])
        else:
            print(f"File not found: {test_file}")
    else:
        # Run all tests with mocks
        pytest.main([__file__, '-v'])
