from loguru import logger
from typing import Dict, Any, Union, Optional
import pytesseract
from PIL import Image
from .interface import ImageExtractorInterface
from ..logger_decorator import log_extractor_method


class TesseractImageExtractor(ImageExtractorInterface):
    def __init__(self):
        self._last_result = None

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "Tesseract",
            "type": "sync",
            "supports": ["text"],
            "description": "Extracts text from image files using Tesseract OCR."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> dict:
        """
        Extracts text from an image file using Tesseract OCR.
        Returns a dictionary with 'content' and 'metadata' keys.
        """
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            
            result = {
                "content": {
                    "TEXT": text.strip()
                },
                "metadata": {
                    "extractor": "Tesseract",
                    "width": image.width,
                    "height": image.height
                }
            }
            
            self._last_result = result
            return result
        except Exception as e:
            logger.error(f"Tesseract image extraction failed: {str(e)}")
            raise e

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Tesseract is synchronous; always returns 'succeeded'.
        """
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is irrelevant for sync extractors; returns last result.
        """
        return self._last_result or {}

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        """
        Tesseract does not support webhooks.
        """
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for Tesseract.
        """
        raise NotImplementedError("Tesseract does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, image_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for Tesseract extraction.
        Tesseract is free (open source library).
        """
        from src.cost_calculator import cost_calculator
        usage_data = {"image_count": image_count}
        cost_metrics = cost_calculator.calculate_cost(
            extractor_name="Tesseract",
            usage_data=usage_data,
            api_response=api_response
        )
        return cost_metrics.calculated_cost

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for Tesseract extraction.
        """
        return {
            "extractor": "Tesseract",
            "image_count": 1,
            "estimated_cost": self.calculate_cost(1, api_response)
        }

