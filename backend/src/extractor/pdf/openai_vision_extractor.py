import openai
import fitz  # PyMuPDF
import base64
from loguru import logger
from typing import Dict, Any, Union
from .interface import PDFExtractorInterface
from src.constants import OPENAI_API_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method

class OpenAIVisionExtractor(PDFExtractorInterface):
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
            # GPT-5 models may take longer, use 300 seconds for them, 60 for others
            timeout = 300.0 if self.model_name in ("gpt-5", "gpt-5-mini") else 60.0
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
            "description": f"Extract text from PDFs using OpenAI Vision model {display_name} with structure preservation."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extract text from PDF using OpenAI Vision API.
        Converts each page to image and processes separately.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}

        try:
            # OpenAI Vision document extractor only handles PDFs
            if not file_path.lower().endswith('.pdf'):
                raise ValueError(f"OpenAI Vision document extractor only supports PDF files, got: {file_path}")
            
            # Process PDF by converting pages to images
            page_contents = self._process_pdf(file_path)

        except RuntimeError as e:
            # Re-raise API errors and timeouts so the task can handle them properly
            if "OpenAI Vision API" in str(e):
                logger.error(f"OpenAI Vision API error in read: {str(e)}")
                raise
            # For other runtime errors, also re-raise
            raise
        except Exception as e:
            logger.error(f"OpenAI Vision extraction failed: {str(e)}")
            # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
            display_name = self._get_display_name()
            page_contents = {
                1: {
                    "content": {
                        "TEXT": ""
                    },
                    "metadata": {
                        "extractor": f"OpenAI {display_name}",
                        "error": str(e)
                    }
                }
            }

        self._last_result = page_contents
        return page_contents

    def _process_pdf(self, file_path: str) -> Dict[int, Dict[str, Any]]:
        """Process PDF by converting each page to image and extracting text."""
        page_contents = {}
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(file_path)
            logger.info(f"Processing PDF with {doc.page_count} pages using {self.model_name}")
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                logger.info(f"Processing page {page_num + 1}/{doc.page_count}")
                
                # Convert page to image
                pix = page.get_pixmap(dpi=200)  # 200 DPI for good quality
                img_bytes = pix.tobytes("png")
                
                # Extract text from this page
                text = self._extract_text_from_image(img_bytes)
                logger.info(f"Extracted {len(text)} characters from page {page_num + 1}")
                
                # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
                display_name = self._get_display_name()
                page_contents[page_num + 1] = {
                    "content": {
                        "TEXT": text
                    },
                    "metadata": {
                        "extractor": f"OpenAI {display_name}",
                        "page_number": page_num + 1,
                        "model": self.model_name
                    }
                }
            
            doc.close()
            logger.info(f"Completed processing PDF, extracted {len(page_contents)} pages")
            
        except RuntimeError as e:
            # Re-raise API errors and timeouts so the task can handle them properly
            if "OpenAI Vision API" in str(e):
                logger.error(f"OpenAI Vision API error in PDF processing: {str(e)}")
                raise
            # For other runtime errors, also re-raise
            raise
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            # For non-API errors, return empty content with error metadata
            # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
            display_name = self._get_display_name()
            page_contents[1] = {
                "content": {
                    "TEXT": ""
                },
                "metadata": {
                    "extractor": f"OpenAI {display_name}",
                    "error": str(e)
                }
            }
        
        return page_contents

    def _extract_text_from_image(self, img_bytes: bytes) -> str:
        """Extract text from image bytes using OpenAI Vision API."""
        try:
            # Encode image as base64
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            logger.debug(f"Calling OpenAI API for image ({len(img_bytes)} bytes, base64: {len(base64_image)} chars)")
            
            # Call OpenAI Vision API with timeout
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
                   api_params["reasoning_effort"] = "minimal"  
                   # minimal reasoning effort for GPT-5 models
                   #api_params["max_completion_tokens"] = 4096
            else:
                api_params["max_tokens"] = 4096
            
            response = client.chat.completions.create(**api_params)
            
            text = response.choices[0].message.content
            extracted_text = text.strip() if text else ""
            logger.debug(f"OpenAI API returned {len(extracted_text)} characters")
            return extracted_text
            
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
        return self._last_result

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

    def calculate_cost(self, page_count: int, **kwargs) -> float:
        """
        Calculate cost for OpenAI Vision based on page count and model.
        """
        return self.cost_calculator.calculate_document_cost(
            service_name="openai-vision",
            page_count=page_count,
            model=self.model_name,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for OpenAI Vision.
        """
        try:
            # Get page count from PDF
            doc = fitz.open(file_path)
            page_count = doc.page_count
            doc.close()
            
            return {
                "page_count": page_count,
                "service": "openai-vision",
                "model": self.model_name,
                "estimated_cost": self.calculate_cost(page_count, **kwargs)
            }
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return {
                "page_count": 0,
                "service": "openai-vision",
                "model": self.model_name,
                "estimated_cost": 0.0
            }
