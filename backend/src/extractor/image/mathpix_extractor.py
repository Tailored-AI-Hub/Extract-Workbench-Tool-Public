from loguru import logger
import requests
from typing import Dict, Any, Union
from .interface import ImageExtractorInterface
from src.constants import MATHPIX_APP_ID, MATHPIX_APP_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method


class MathpixImageExtractor(ImageExtractorInterface):
    def __init__(self):
        """
        Initialize Mathpix image extractor with API credentials.
        """
        self.app_id = MATHPIX_APP_ID
        self.app_key = MATHPIX_APP_KEY
        self._last_result = None
        self.image_endpoint = "https://api.mathpix.com/v3/text"
        self.cost_calculator = CostCalculator()
    
    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "Mathpix",
            "type": "sync",
            "supports": ["text", "latex", "markdown"],
            "description": "Extracts text and math expressions from images using Mathpix API."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> dict:
        """
        Process image file using Mathpix API synchronously.
        Returns a dictionary with 'content' and 'metadata' keys.
        """
        headers = {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                
                response = requests.post(
                    self.image_endpoint,
                    headers=headers,
                    files=files
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract text field (Mathpix Markdown with LaTeX)
            text_content = result.get('text', '').strip()
            latex_styled = result.get('latex_styled', '').strip()
            
            # Use latex_styled if available, otherwise use text
            content_text = latex_styled if latex_styled else text_content
            
            formatted_result = {
                "content": {
                    "TEXT": content_text,
                    "LATEX": content_text
                },
                "metadata": {
                    "extractor": "Mathpix",
                    "request_id": result.get('request_id', ''),
                    "confidence": result.get('confidence', 0),
                    "confidence_rate": result.get('confidence_rate', 0),
                    "is_handwritten": result.get('is_handwritten', False),
                    "is_printed": result.get('is_printed', False),
                    "format": "image_sync"
                }
            }
            
            self._last_result = formatted_result
            logger.info(f"Mathpix image processed successfully. Extracted {len(content_text)} characters")
            return formatted_result

        except requests.exceptions.HTTPError as e:
            error_msg = f"Mathpix API request failed: {e}"
            if hasattr(e.response, 'text'):
                error_msg += f" Response: {e.response.text}"
            logger.error(error_msg)
            raise
        except Exception as e:
            logger.error(f"Mathpix image processing failed: {str(e)}")
            raise

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Mathpix image processing is synchronous; always returns 'succeeded'.
        """
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        job_id is unused for sync extractors; returns last result.
        """
        return self._last_result or {}

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        raise NotImplementedError("Mathpix does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, image_count: int, **kwargs) -> float:
        """
        Calculate cost for Mathpix based on image count.
        """
        return self.cost_calculator.calculate_image_cost(
            service_name="mathpix",
            image_count=image_count,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for Mathpix.
        """
        return {
            "image_count": 1,
            "service": "mathpix",
            "estimated_cost": self.calculate_cost(1, **kwargs)
        }

