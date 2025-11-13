from loguru import logger
import requests
from typing import Dict, Any, Union
from .interface import PDFExtractorInterface
from src.constants import MATHPIX_APP_ID, MATHPIX_APP_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method

class MathpixExtractor(PDFExtractorInterface):
    def __init__(self):
        """
        Initialize Mathpix extractor with API credentials.
        """
        self.app_id = MATHPIX_APP_ID
        self.app_key = MATHPIX_APP_KEY
        self._last_result = None
        self.pdf_endpoint = "https://api.mathpix.com/v3/pdf"
        self.cost_calculator = CostCalculator()
    
    def _is_pdf_file(self, file_path: str) -> bool:
        """
        Check if file is a PDF based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is a PDF, False otherwise
        """
        return file_path.lower().endswith('.pdf')

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "Mathpix",
            "type": "async",
            "supports": ["text", "latex", "markdown"],
            "description": "Extracts text and math expressions from PDFs using Mathpix API. PDFs are processed asynchronously."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Union[str, Dict[int, Dict[str, Any]]]:
        """
        Upload PDF file to Mathpix and return job ID for async processing.
        Returns: job ID (string) for async processing
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            # Mathpix document extractor only handles PDFs
            if not self._is_pdf_file(file_path):
                raise ValueError(f"Mathpix document extractor only supports PDF files, got: {file_path}")
            
            # PDF processing (async)
            self._last_result = None
            
            with open(file_path, 'rb') as f:
                files = {'file': f}
                
                response = requests.post(
                    self.pdf_endpoint,
                    headers=headers,
                    files=files
                )
            
            response.raise_for_status()
            result = response.json()
            pdf_id = result.get('pdf_id')
            
            if not pdf_id:
                raise ValueError(f"No pdf_id in response: {result}")
            
            logger.info(f"PDF uploaded successfully. PDF ID: {pdf_id}")
            return pdf_id

        except requests.exceptions.HTTPError as e:
            error_msg = f"Mathpix API request failed: {e}"
            if hasattr(e.response, 'text'):
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"Mathpix file processing failed: {str(e)}")
            raise

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Check the processing status for PDF jobs.
        
        Returns: 'succeeded', 'processing', 'failed'
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            response = requests.get(
                f"{self.pdf_endpoint}/{job_id}",
                headers=headers
            )
            response.raise_for_status()
            
            status_data = response.json()
            status = status_data.get('status', 'unknown')
            
            # Map Mathpix status to our standard statuses
            if status == 'completed':
                return 'succeeded'
            elif status == 'error':
                error_info = status_data.get('error', 'Unknown error')
                logger.error(f"Mathpix PDF processing failed for job {job_id}: {error_info}")
                logger.error(f"Full response: {response.text}")
                return 'failed'
            else:
                return 'processing'

        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to check PDF status: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            return 'failed'
        except Exception as e:
            logger.error(f"Failed to check status: {str(e)}")
            return 'failed'

    @log_extractor_method()
    def get_result(self, job_id: str, output_format: str = 'mmd') -> Union[str, dict]:
        """
        Get the processed results from Mathpix for PDF jobs.
        
        Args:
            job_id: The PDF ID returned from read()
            output_format: Ignored - we use lines.json format for PDFs
        
        Returns:
            Dict with page contents in the standard format
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            # Get the structured lines data from Mathpix
            lines_response = requests.get(
                f"{self.pdf_endpoint}/{job_id}.lines.json",
                headers=headers
            )
            lines_response.raise_for_status()
            lines_data = lines_response.json()
            
            # Parse the structured response
            page_contents: Dict[int, Dict[str, Any]] = {}
            
            if 'pages' in lines_data and isinstance(lines_data['pages'], list):
                for page_data in lines_data['pages']:
                    page_num = page_data.get('page', 1)
                    lines = page_data.get('lines', [])
                    
                    # Sort lines by line number
                    sorted_lines = sorted(lines, key=lambda x: x.get('line', 0))
                    
                    # Collect text from text_display field, filtering out empty ones
                    page_text_lines = []
                    for line in sorted_lines:
                        text_display = line.get('text_display', '').strip()
                        if text_display:  # Only include non-empty text
                            page_text_lines.append(text_display)
                    
                    # Join all text lines for this page
                    page_text = '\n'.join(page_text_lines)
                    
                    # Only TEXT is present (LATEX is same content), so COMBINED is not added (requires at least 2 content types)
                    page_contents[page_num] = {
                        "content": {
                            "TEXT": page_text,
                            "LATEX": page_text  # Using the same text for both TEXT and LATEX
                        },
                        "metadata": {
                            "extractor": "Mathpix",
                            "pdf_id": job_id,
                            "page": page_num,
                            "total_lines": len(sorted_lines),
                            "format": "lines.json"
                        }
                    }
                    
                    logger.info(f"Processed page {page_num} with {len(page_text_lines)} text lines")
            else:
                # Fallback if pages structure is not as expected
                logger.warning("Unexpected response structure from Mathpix lines.json")
                # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
                page_contents[1] = {
                    "content": {
                        "TEXT": "",
                        "LATEX": ""
                    },
                    "metadata": {
                        "extractor": "Mathpix",
                        "pdf_id": job_id,
                        "page": 1,
                        "error": "Unexpected response structure"
                    }
                }
            
            self._last_result = page_contents
            return page_contents

        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to get PDF results: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
            return {
                1: {
                    "content": {
                        "TEXT": "",
                        "LATEX": ""
                    },
                    "metadata": {"error": error_msg}
                }
            }
        except Exception as e:
            logger.error(f"Failed to get results: {str(e)}")
            # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
            return {
                1: {
                    "content": {
                        "TEXT": "",
                        "LATEX": ""
                    },
                    "metadata": {"error": str(e)}
                }
            }

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("Mathpix does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, page_count: int, **kwargs) -> float:
        """
        Calculate cost for Mathpix based on page count.
        """
        return self.cost_calculator.calculate_document_cost(
            service_name="mathpix",
            page_count=page_count,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for Mathpix.
        """
        try:
            # Get page count from PDF
            import fitz
            doc = fitz.open(file_path)
            page_count = doc.page_count
            doc.close()
            
            return {
                "page_count": page_count,
                "service": "mathpix",
                "estimated_cost": self.calculate_cost(page_count, **kwargs)
            }
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return {
                "page_count": 0,
                "service": "mathpix",
                "estimated_cost": 0.0
            }