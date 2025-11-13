from loguru import logger
from typing import Dict, Any, Union, Optional
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from io import BytesIO
from .interface import PDFExtractorInterface
from ..logger_decorator import log_extractor_method


class TesseractExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "Tesseract",
            "type": "sync",
            "supports": ["text"],
            "description": "Extracts text from scanned PDFs using Tesseract OCR by converting PDF pages to images."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extracts text from each page of a scanned PDF using Tesseract OCR.
        Converts PDF pages to images for OCR processing.
        """
        page_contents: Dict[int, Dict[str, Any]] = {}
        try:
            # Tesseract document extractor only handles PDFs
            if not file_path.lower().endswith(".pdf"):
                raise ValueError(f"Tesseract document extractor only supports PDF files, got: {file_path}")
            
            # Convert each page to an image using PyMuPDF (no Poppler needed)
            images = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    img_bytes = pix.tobytes("png")
                    images.append(Image.open(BytesIO(img_bytes)))
            
            for i, image in enumerate(images, start=1):
                text = pytesseract.image_to_string(image)
                text_stripped = text.strip()
                # Only TEXT is present, so COMBINED is not added (requires at least 2 content types)
                page_contents[i] = {
                    "content": {
                        "TEXT": text_stripped
                    },
                    "metadata": {
                        "extractor": "Tesseract",
                        "page_number": i
                    }
                }
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {str(e)}")
            raise e
        self._last_result = page_contents
        return page_contents

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
        return self._last_result

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
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for Tesseract extraction.
        Tesseract is free (open source library).
        """
        from src.cost_calculator import CostCalculator
        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("Tesseract", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for Tesseract extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "Tesseract",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }
