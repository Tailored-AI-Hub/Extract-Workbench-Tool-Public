from typing import Dict, Any, Union, Optional
from PyPDF2 import PdfReader
from .interface import PDFExtractorInterface
from loguru import logger
from ..logger_decorator import log_extractor_method




class PyPDF2Extractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "PyPDF2",
            "type": "sync",
            "supports": ["text"],
            "description": "Extracts text content from PDFs using PyPDF2."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extracts raw text from PDF pages using PyPDF2 synchronously.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}
        try:
            reader = PdfReader(file_path)
            num_pages = len(reader.pages)
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text = page.extract_text() or ""
                page_contents[page_num + 1] = {
                    "content": {
                        "TEXT": text
                    },
                    "metadata": {
                        "extractor": "PyPDF2",
                        "page_number": page_num + 1
                    }
                }
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {str(e)}")
            page_contents = {
                1: {
                    "content": {"TEXT": ""},
                    "metadata": {"error": str(e)}
                }
            }
        self._last_result = page_contents
        return page_contents

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        PyPDF2 is synchronous; always returns 'succeeded'.
        """
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is irrelevant for synchronous extractors; returns last result.
        """
        return self._last_result

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        """
        PyPDF2 does not support webhooks.
        """
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for PyPDF2.
        """
        raise NotImplementedError("PyPDF2 does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for PyPDF2 extraction.
        PyPDF2 is free (open source library).
        """
        from src.cost_calculator import CostCalculator
        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("PyPDF2", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for PyPDF2 extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "PyPDF2",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }
