import os
from loguru import logger
from typing import Dict, Any, Union, Optional
from botocore.session import get_session
from .interface import ImageExtractorInterface
from src.constants import AWS_BUCKET_NAME, AWS_REGION
from ..logger_decorator import log_extractor_method


class TextractImageExtractor(ImageExtractorInterface):
    def __init__(self) -> None:
        self.region = AWS_REGION or os.getenv("AWS_REGION") or "us-east-1"
        self._session = None
        self._textract = None
        self._last_result = None

    def _ensure_clients(self) -> None:
        if self._session is None:
            self._session = get_session()  # picks up env/instance creds
        if self._textract is None:
            self._textract = self._session.create_client("textract", region_name=self.region)

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "AWS Textract",
            "type": "sync",
            "supports": ["text"],
            "description": "Extracts text from image files using AWS Textract."
        }

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> dict:
        return {}

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> dict:
        """
        Extract text from image file using AWS Textract.
        Returns a dictionary with 'content' and 'metadata' keys.
        """
        self._ensure_clients()
        
        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
            
            resp = self._textract.detect_document_text(Document={"Bytes": image_bytes})
            blocks = resp.get("Blocks", [])
            
            # Extract text from LINE blocks
            lines = []
            for block in blocks:
                if block.get("BlockType") == "LINE":
                    text = (block.get("Text") or "").strip()
                    if text:
                        lines.append(text)
            
            text_content = "\n".join(lines)
            
            result = {
                "content": {
                    "TEXT": text_content
                },
                "metadata": {
                    "extractor": "AWS Textract",
                    "block_count": len(blocks),
                    "line_count": len(lines)
                }
            }
            
            self._last_result = result
            return result
        except Exception as e:
            logger.error(f"Textract image extraction failed: {str(e)}")
            raise e

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> dict:
        return self._last_result or {}

    @log_extractor_method()
    def calculate_cost(self, image_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for AWS Textract extraction.
        """
        from src.cost_calculator import cost_calculator
        usage_data = {"image_count": image_count}
        cost_metrics = cost_calculator.calculate_cost(
            extractor_name="Textract",
            usage_data=usage_data,
            api_response=api_response
        )
        return cost_metrics.calculated_cost

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for AWS Textract extraction.
        """
        return {
            "extractor": "AWS Textract",
            "image_count": 1,
            "estimated_cost": self.calculate_cost(1, api_response)
        }

