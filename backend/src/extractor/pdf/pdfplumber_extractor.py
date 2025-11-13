import pdfplumber
from typing import Dict, Any, Union, Optional
from .interface import PDFExtractorInterface
from ..logger_decorator import log_extractor_method

class PDFPlumberExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "PDFPlumber",
            "type": "sync",
            "supports": ["combined", "tables"],
            "description": "Extracts text and tables from PDFs using PDFPlumber."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Dict[str, str]]]:
        """
        Extract text and tables from PDF synchronously.
        Stores result internally and returns it directly.
        """
        page_contents = {}

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text (includes table content as text too)
                text = page.extract_text()

                # Extract tables separately
                tables = page.extract_tables()

                # Format tables into string representation
                table_strings = []
                if tables:
                    for table in tables:
                        if table:
                            table_str = ""
                            for row in table:
                                if row:
                                    table_str += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
                            table_strings.append(table_str.strip())

                # Build content with separate TEXT and TABLE fields
                text_content = text or ""
                table_content = "\n\n".join(table_strings) if table_strings else ""
                
                content = {}
                content_parts = []
                
                if text_content:
                    content["TEXT"] = text_content
                    content_parts.append(text_content)
                if table_content:
                    content["TABLE"] = table_content
                    content_parts.append(table_content)
                
                # Only add COMBINED if at least two content types are present
                if len(content_parts) >= 2:
                    content["COMBINED"] = "\n\n".join(content_parts)

                page_contents[page_num] = {"content": content}

        self._last_result = page_contents
        return page_contents

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        # Always succeeds immediately since pdfplumber is sync
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        # job_id is irrelevant for sync; just return last result
        return self._last_result

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        # Local libraries don't support webhooks
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("PDFPlumber does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for PDFPlumber extraction.
        PDFPlumber is free (open source library).
        """
        from src.cost_calculator import CostCalculator
        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("PDFPlumber", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for PDFPlumber extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "PDFPlumber",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }