import fitz  # PyMuPDF
from typing import Dict, Any, Union, Optional
from .interface import PDFExtractorInterface
from ..logger_decorator import log_extractor_method

class PyMuPDFExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "PyMuPDF",
            "type": "sync",
            "supports": ["text"],   # PyMuPDF is mainly for text, not structured tables
            "description": "Extracts raw text (and metadata if needed) using PyMuPDF (fitz)."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, str]]:
        """
        Extract text from PDF using PyMuPDF synchronously.
        """
        page_contents: Dict[int, Dict[str, str]] = {}

        doc = fitz.open(file_path)

        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()

            page_contents[page_num + 1] = {
                "content": {
                    "TEXT": text or ""
                }
            }

        doc.close()
        self._last_result = page_contents
        return page_contents

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        # Always succeeds immediately since PyMuPDF is sync
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        # job_id is irrelevant for sync; return last result
        return self._last_result

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("PyMuPDF does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for PyMuPDF extraction.
        PyMuPDF is free (open source library).
        """
        from src.cost_calculator import CostCalculator
        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("PyMuPDF", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for PyMuPDF extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "PyMuPDF",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }
