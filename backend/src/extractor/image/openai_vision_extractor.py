import openai
import base64
from loguru import logger
from typing import Dict, Any, Union
from .interface import ImageExtractorInterface
from src.constants import OPENAI_API_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method


class OpenAIVisionImageExtractor(ImageExtractorInterface):
    def __init__(self, model_name: str):
        """
        Initialize OpenAI Vision extractor with specified model.
        
        Args:
            model_name: OpenAI model name (gpt-4o-mini, gpt-4o, gpt-5, gpt-5-mini)
        """
        self.model_name = model_name
        self._last_result = None
        # Initialize client lazily to avoid errors when just getting information
        self._client = None
        self._api_key = OPENAI_API_KEY
        self.cost_calculator = CostCalculator()
    
    def _get_client(self):
        """Get OpenAI client, initializing it if needed."""
        if self._client is None:
            # GPT-5 models may take longer, use 120 seconds for them, 60 for others
            timeout = 120.0 if self.model_name in ("gpt-5", "gpt-5-mini") else 60.0
            self._client = openai.OpenAI(
                api_key=self._api_key,
                timeout=timeout
            )
        return self._client
    
    def _get_display_name(self) -> str:
        """Get formatted display name for the model."""
        model_name_map = {
            "gpt-5": "GPT-5",
            "gpt-5-mini": "GPT-5 Mini",
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini"
        }
        return model_name_map.get(self.model_name, self.model_name.upper())

    @log_extractor_method()
    def get_information(self) -> dict:
        display_name = self._get_display_name()
        return {
            "name": f"OpenAI {display_name}",
            "type": "sync",
            "supports": ["text", "image", "structure"],
            "description": f"Extract text from images using OpenAI Vision model {display_name} with structure preservation."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> dict:
        """
        Extract text from image file using OpenAI Vision API.
        Returns a dictionary with 'content' and 'metadata' keys.
        """
        try:
            with open(file_path, 'rb') as f:
                img_bytes = f.read()
            
            text = self._extract_text_from_image(img_bytes)
            
            display_name = self._get_display_name()
            result = {
                "content": {
                    "TEXT": text
                },
                "metadata": {
                    "extractor": f"OpenAI {display_name}",
                    "model": self.model_name
                }
            }
            
            self._last_result = result
            return result
        except RuntimeError as e:
            # Re-raise API errors and timeouts so the task can handle them properly
            if "OpenAI Vision API" in str(e):
                logger.error(f"OpenAI Vision API error in read: {str(e)}")
                raise
            # For other runtime errors, also re-raise
            raise
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {str(e)}")
            display_name = self._get_display_name()
            return {
                "content": {
                    "TEXT": ""
                },
                "metadata": {
                    "extractor": f"OpenAI {display_name}",
                    "error": str(e)
                }
            }

    def _extract_text_from_image(self, img_bytes: bytes) -> str:
        """Extract text from image bytes using OpenAI Vision API."""
        try:
            # Encode image as base64
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            
            # Call OpenAI Vision API
            client = self._get_client()
            
            # GPT-5 models use max_completion_tokens instead of max_tokens
            api_params = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image preserving structure and formatting. Return only the extracted text."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Use max_completion_tokens for GPT-5 models, max_tokens for older models
            if self.model_name in ("gpt-5", "gpt-5-mini"):
                api_params["max_completion_tokens"] = 4096
            else:
                api_params["max_tokens"] = 4096
            
            response = client.chat.completions.create(**api_params)
            
            text = response.choices[0].message.content
            return text.strip() if text else ""
            
        except (openai.APITimeoutError, TimeoutError) as e:
            logger.error(f"OpenAI Vision API timeout error: {str(e)}")
            # Timeout errors should be raised immediately to prevent jobs from getting stuck
            raise RuntimeError(f"OpenAI Vision API timeout: {str(e)}") from e
        except openai.APIError as e:
            logger.error(f"OpenAI Vision API error: {str(e)}")
            # For API errors, raise the exception so the task can properly handle it as a failure
            # This prevents jobs from getting stuck or completing with error content
            raise RuntimeError(f"OpenAI Vision API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"OpenAI Vision API unexpected error: {str(e)}")
            # For any other errors, also raise to prevent jobs from getting stuck
            raise RuntimeError(f"OpenAI Vision API error: {str(e)}") from e

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        OpenAI Vision is synchronous; extraction always completes immediately.
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
        """
        OpenAI Vision does not support webhooks.
        """
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for OpenAI Vision.
        """
        raise NotImplementedError("OpenAI Vision does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, image_count: int, **kwargs) -> float:
        """
        Calculate cost for OpenAI Vision based on image count and model.
        """
        return self.cost_calculator.calculate_image_cost(
            service_name="openai-vision",
            image_count=image_count,
            model=self.model_name,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for OpenAI Vision.
        """
        return {
            "image_count": 1,
            "service": "openai-vision",
            "model": self.model_name,
            "estimated_cost": self.calculate_cost(1, **kwargs)
        }

