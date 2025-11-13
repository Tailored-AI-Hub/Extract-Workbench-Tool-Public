from markitdown import MarkItDown
from typing import Dict, Any, Union, Optional
from .interface import PDFExtractorInterface
from loguru import logger
from ..logger_decorator import log_extractor_method


class MarkItDownExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "MarkItDown",
            "type": "sync",
            "supports": ["text", "tables", "markdown"],
            "description": "Extracts text and converts to markdown format using MarkItDown."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs):
        """
        Extract text from PDF and convert to markdown using MarkItDown synchronously.
        Returns a per-page mapping with extracted markdown content.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}
        try:
            # Create MarkItDown instance and process the document
            md = MarkItDown()
            result = md.convert(file_path)
            
            # Extract text content and ensure it's not empty
            text_content = result.text_content if result.text_content else ""
            
            # Add debug logging to help troubleshoot content extraction
            logger.info(f"MarkItDown extracted content length: {len(text_content)}")
            if text_content:
                logger.debug(f"MarkItDown extracted content preview: {text_content[:200]}...")
            
            # MarkItDown returns the full document content as markdown
            # We'll treat it as a single page for now, but could be split by pages if needed
            content = {
                "MARKDOWN": text_content,
                "TEXT": text_content  # Also provide as plain text
            }
            # Only add COMBINED if at least two distinct content types are present
            # Since MARKDOWN and TEXT are the same content, COMBINED is not added
            page_contents[1] = {
                "content": content,
                "metadata": {
                    "extractor": "MarkItDown",
                    "format": "markdown",
                    "total_pages": 1
                }
            }
        except Exception as e:
            logger.warning(f"MarkItDown extraction failed: {str(e)}")
            page_contents = {
                1: {
                    "content": {
                        "MARKDOWN": "",
                        "TEXT": ""
                    },
                    "metadata": {"error": str(e)}
                }
            }
        self._last_result = page_contents
        return page_contents

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        MarkItDown is synchronous; extraction always completes immediately.
        """
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is unused for sync extractors; returns last result.
        """
        return self._last_result

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        """
        MarkItDown does not support webhooks.
        """
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for MarkItDown.
        """
        raise NotImplementedError("MarkItDown does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for MarkItDown extraction.
        MarkItDown is free (open source library).
        """
        from src.cost_calculator import CostCalculator
        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("MarkItDown", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for MarkItDown extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "MarkItDown",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }
