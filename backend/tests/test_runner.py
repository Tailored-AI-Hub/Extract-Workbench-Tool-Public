"""
Pytest-based test runner for PDF extractors.
Provides a unified interface to run all tests with different configurations.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def run_pytest_tests(pdf_file=None, extractor=None, mock_only=False, real_only=False, verbose=False):
    """Run pytest tests with specified options."""
    cmd = ['python', '-m', 'pytest']
    
    # Add verbosity
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    # Add markers for test selection
    if mock_only:
        cmd.extend(['-m', 'not real_file'])
    elif real_only:
        cmd.extend(['-m', 'real_file'])
    
    # Add PDF file if provided
    if pdf_file:
        cmd.extend(['--pdf-file', pdf_file])
    
    # Add specific test file if extractor specified
    if extractor:
        test_files = {
            'markitdown': 'test_markitdown_extractor.py',
            'llamaparse': 'test_llamaparse_extractor.py',
            'unstructured': 'test_unstructured_extractor.py',
            'pypdf2': 'test_existing_extractors.py::test_pypdf2',
            'pymupdf': 'test_existing_extractors.py::test_pymupdf',
            'pdfplumber': 'test_existing_extractors.py::test_pdfplumber',
            'camelot': 'test_existing_extractors.py::test_camelot',
            'tesseract': 'test_existing_extractors.py::test_tesseract'
        }
        
        if extractor.lower() in test_files:
            cmd.append(test_files[extractor.lower()])
        else:
            print(f"❌ Unknown extractor: {extractor}")
            print(f"Available extractors: {', '.join(test_files.keys())}")
            return False
    
    # Add test directory
    cmd.append('tests/')
    
    print(f"🧪 Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def run_mock_tests():
    """Run all tests with mocked dependencies."""
    print("🧪 Running mock tests (no external dependencies)...")
    return run_pytest_tests(mock_only=True, verbose=True)


def run_real_file_tests(pdf_file_path):
    """Run tests with a real PDF file."""
    print(f"📄 Running real file tests with: {pdf_file_path}")
    
    if not os.path.exists(pdf_file_path):
        print(f"❌ File not found: {pdf_file_path}")
        return False
    
    return run_pytest_tests(pdf_file=pdf_file_path, real_only=True, verbose=True)


def run_specific_extractor_tests(extractor_name, pdf_file_path=None):
    """Run tests for a specific extractor."""
    print(f"🎯 Running tests for {extractor_name}...")
    
    return run_pytest_tests(
        pdf_file=pdf_file_path, 
        extractor=extractor_name, 
        verbose=True
    )


def run_all_tests(pdf_file_path=None):
    """Run all tests."""
    print("🔄 Running all tests...")
    
    # First run mock tests
    print("\n1️⃣ Running mock tests...")
    mock_success = run_pytest_tests(mock_only=True, verbose=True)
    
    # Then run real file tests if file provided
    real_success = True
    if pdf_file_path:
        print(f"\n2️⃣ Running real file tests with: {pdf_file_path}")
        real_success = run_pytest_tests(pdf_file=pdf_file_path, real_only=True, verbose=True)
    else:
        print("\n💡 Tip: Use --file to test with a real PDF file")
    
    return mock_success and real_success


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description='PDF Extractor Test Runner (pytest-based)')
    parser.add_argument('--file', '-f', help='Path to PDF file for real file testing')
    parser.add_argument('--extractor', '-e', help='Test specific extractor')
    parser.add_argument('--mock-only', action='store_true', help='Run only mock tests')
    parser.add_argument('--real-only', action='store_true', help='Run only real file tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    print("🚀 PDF Extractor Test Runner (pytest)")
    print("=" * 50)
    
    success = False
    
    if args.mock_only:
        # Run only mock tests
        success = run_mock_tests()
        
    elif args.real_only:
        # Run only real file tests
        if not args.file:
            print("❌ Real file tests require --file argument")
            return 1
        success = run_real_file_tests(args.file)
        
    elif args.extractor:
        # Run specific extractor tests
        success = run_specific_extractor_tests(args.extractor, args.file)
        
    else:
        # Run all tests
        success = run_all_tests(args.file)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests completed successfully!")
        return 0
    else:
        print("❌ Some tests failed. Check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())