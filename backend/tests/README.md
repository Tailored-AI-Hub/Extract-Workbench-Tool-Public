# PDF Extractor Tests (pytest-based)

This directory contains comprehensive pytest-based tests for all PDF extractors in the system.

## Test Structure

### Pytest Configuration (`conftest.py`)
- **Location**: `conftest.py`
- **Purpose**: Pytest configuration and shared fixtures
- **Features**:
  - Shared fixtures for all extractors
  - Command-line options for test selection
  - Markers for different test types
  - Test collection customization

### Base Test Utilities (`base_test.py`)
- **Location**: `base_test.py`
- **Purpose**: Common test utilities and fixtures using pytest
- **Features**:
  - Pytest fixtures for common test setup
  - Interface validation functions
  - Error handling tests
  - Webhook support tests

### Individual Extractor Tests

#### New Extractors
- **`test_markitdown_extractor.py`** - Tests for MarkItDown extractor
- **`test_llamaparse_extractor.py`** - Tests for LlamaParse extractor  
- **`test_unstructured_extractor.py`** - Tests for Unstructured extractor

#### Existing Extractors
- **`test_existing_extractors.py`** - Tests for all existing extractors:
  - PyPDF2
  - PyMuPDF
  - PDFPlumber
  - Camelot
  - Tesseract

### Test Runner (`test_runner.py`)
- **Purpose**: Unified pytest-based interface to run all tests
- **Features**:
  - Mock testing (no external dependencies)
  - Real file testing (integration tests)
  - Specific extractor testing
  - Command-line interface
  - Pytest integration

## Usage

### Running All Tests
```bash
# Run all tests with mocked dependencies
python test_runner.py

# Run all tests with a real PDF file
python test_runner.py --file /path/to/your/document.pdf

# Run only mock tests
python test_runner.py --mock-only

# Run only real file tests
python test_runner.py --real-only --file /path/to/your/document.pdf
```

### Running Specific Extractor Tests
```bash
# Test MarkItDown extractor
python test_runner.py --extractor markitdown

# Test LlamaParse extractor with real file
python test_runner.py --extractor llamaparse --file /path/to/your/document.pdf

# Test Unstructured extractor
python test_runner.py --extractor unstructured

# Test existing extractors
python test_runner.py --extractor pypdf2
python test_runner.py --extractor pymupdf
python test_runner.py --extractor pdfplumber
python test_runner.py --extractor camelot
python test_runner.py --extractor tesseract
```

### Direct Pytest Usage
```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run only mock tests
pytest tests/ -m "not real_file"

# Run only real file tests
pytest tests/ -m "real_file" --pdf-file /path/to/document.pdf

# Run specific test file
pytest tests/test_markitdown_extractor.py

# Run specific test function
pytest tests/test_markitdown_extractor.py::test_read_success

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Test Types and Markers

### Test Markers
- **`@pytest.mark.mock`** - Tests using mocked dependencies
- **`@pytest.mark.real_file`** - Tests requiring real PDF files
- **`@pytest.mark.slow`** - Slow-running tests
- **`@pytest.mark.integration`** - Integration tests
- **`@pytest.mark.unit`** - Unit tests

### Fixtures
- **`extractor`** - Individual extractor instances
- **`test_pdf_path`** - Path to test PDF file
- **`any_extractor`** - Parametrized fixture for all extractors

## Test Coverage

### Interface Tests
- ✅ All required methods exist
- ✅ Method return types are correct
- ✅ Error handling works properly
- ✅ Webhook support is correctly implemented

### Functionality Tests
- ✅ Successful extraction scenarios
- ✅ Error handling and edge cases
- ✅ Content structure validation
- ✅ Metadata accuracy

### Integration Tests
- ✅ Real file processing
- ✅ Multi-page document handling
- ✅ Different file formats
- ✅ Performance validation

### Parametrized Tests
- ✅ Multiple test scenarios with different inputs
- ✅ Different element types (for Unstructured)
- ✅ Various status codes (for LlamaParse)
- ✅ Different file paths and formats

## Available Extractors

### New Extractors
1. **MarkItDown** - Synchronous markdown conversion
2. **LlamaParse** - Asynchronous API-based extraction
3. **Unstructured** - Synchronous structured element extraction

### Existing Extractors
1. **PyPDF2** - Basic text extraction
2. **PyMuPDF** - Advanced text extraction
3. **PDFPlumber** - Text and table extraction
4. **Camelot** - Table extraction
5. **Tesseract** - OCR extraction

## Pytest Features Used

### Fixtures
- **Session-scoped fixtures** for expensive setup
- **Function-scoped fixtures** for individual tests
- **Parametrized fixtures** for testing multiple extractors
- **Autouse fixtures** for automatic setup

### Parametrization
- **`@pytest.mark.parametrize`** for multiple test scenarios
- **Parametrized fixtures** for testing all extractors
- **Dynamic test generation** based on available extractors

### Mocking
- **`@patch` decorators** for mocking external dependencies
- **`pytest-mock`** for advanced mocking capabilities
- **Context managers** for temporary mocking

### Markers and Selection
- **Custom markers** for test categorization
- **Command-line selection** of specific test types
- **Conditional test execution** based on available resources

## Test Data

### Mock Data
- All tests use mocked dependencies
- No external API calls
- Predictable test results
- Fast execution

### Real File Testing
- Use actual PDF documents
- Test with various document types
- Validate real-world performance
- End-to-end validation

## Continuous Integration

### GitHub Actions
```yaml
# Example CI configuration
- name: Install Dependencies
  run: pip install -r requirements.txt

- name: Run Mock Tests
  run: python test_runner.py --mock-only

- name: Run Real File Tests
  run: python test_runner.py --real-only --file test_document.pdf

- name: Run with Coverage
  run: pytest tests/ --cov=src --cov-report=xml
```

### Local Development
```bash
# Quick validation
python test_runner.py --mock-only

# Full testing
python test_runner.py --file /path/to/test/document.pdf

# Development with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

## Advanced Usage

### Custom Test Selection
```bash
# Run tests matching a pattern
pytest tests/ -k "test_read"

# Run tests with specific markers
pytest tests/ -m "mock and not slow"

# Run tests in parallel
pytest tests/ -n auto

# Run tests with specific output
pytest tests/ --tb=short
```

### Debugging
```bash
# Run with debugging
pytest tests/ --pdb

# Run with verbose output
pytest tests/ -vv

# Run specific test with debugging
pytest tests/test_markitdown_extractor.py::test_read_success -vv --pdb
```

## Dependencies

### Required for All Tests
- `pytest>=7.0.0`
- `pytest-mock>=3.10.0`
- `pytest-cov>=4.0.0`

### Required for Real File Tests
- All extractor dependencies (see `requirements.txt`)
- Valid PDF files for testing

## Example Usage

```bash
# Test all extractors with a sample PDF
python test_runner.py --file uploads/sample.pdf

# Test only MarkItDown with a specific file
python test_runner.py --extractor markitdown --file uploads/sample.pdf

# Run only mock tests (no file needed)
python test_runner.py --mock-only

# Run only real file tests
python test_runner.py --real-only --file uploads/sample.pdf

# Run with pytest directly
pytest tests/ -v --pdf-file uploads/sample.pdf
```

## Test Results

The test runner provides detailed output including:
- Individual test results
- Success/failure counts
- Error messages
- Performance metrics
- Summary statistics
- Coverage reports (when using --cov)

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the correct directory
   - Check that all dependencies are installed
   - Verify Python path is set correctly

2. **Real File Tests Failing**
   - Verify the PDF file exists and is readable
   - Check that required libraries are installed
   - Some extractors may require additional setup

3. **Mock Tests Failing**
   - Check that mocks are properly configured
   - Verify test data matches expected format
   - Ensure fixtures are properly set up

4. **Pytest Not Found**
   - Install pytest: `pip install pytest`
   - Check that pytest is in your PATH
   - Use `python -m pytest` instead of `pytest`

### Debug Mode
```bash
# Run with verbose output
python test_runner.py --verbose

# Run specific test with debugging
pytest tests/test_markitdown_extractor.py::test_read_success -vv --pdb

# Run with detailed output
pytest tests/ -vv --tb=long
```

## Contributing

### Adding New Tests
1. Follow the existing pytest structure
2. Use fixtures for common setup
3. Add both mock and real file tests
4. Use appropriate markers
5. Update conftest.py if needed

### Test Guidelines
- Use descriptive test names starting with `test_`
- Use fixtures for common setup
- Include both success and failure scenarios
- Test edge cases and error conditions
- Use parametrization for multiple scenarios
- Maintain good test coverage
- Keep tests fast and reliable
- Use appropriate markers for test categorization