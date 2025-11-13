import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .constants import STAGE


class ExtractorType(Enum):
    AUDIO = "audio"
    IMAGE = "image"
    DOCUMENT = "document"


@dataclass
class CostMetrics:
    """Standardized cost metrics for all extractors"""

    calculated_cost: float
    actual_cost: Optional[float] = None
    usage_metrics: Optional[Dict[str, Any]] = None
    cost_source: str = "calculated"  # "api", "langfuse", "calculated"
    discrepancy: Optional[float] = None


# Singleton Langfuse client to avoid multiple initializations
_langfuse_client = None
_langfuse_initialized = False


def _get_langfuse_client():
    """Get or initialize Langfuse client (singleton pattern)"""
    global _langfuse_client, _langfuse_initialized
    
    if _langfuse_initialized:
        return _langfuse_client
    
    _langfuse_initialized = True
    
    # Skip Langfuse initialization for local development
    stage = os.getenv("STAGE", "development").lower()
    if stage == "development":
        return None

    try:
        # Try to import langfuse only when needed
        from langfuse import Langfuse

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        if public_key and secret_key:
            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
            print("Langfuse client initialized successfully")
        else:
            print(
                "Production mode: Langfuse credentials not provided - cost tracking disabled"
            )
    except ImportError:
        print(
            "Warning: Langfuse package not available. Using fallback cost calculation."
        )
    except Exception as e:
        print(f"Failed to initialize Langfuse client: {e}")
    
    return _langfuse_client


class CostCalculator:
    """
    Centralized cost calculation service with Langfuse integration
    """

    def __init__(self):
        # Use singleton Langfuse client
        self.langfuse_client = _get_langfuse_client()

        # Load pricing configuration
        self.pricing_config = self._load_pricing_config()

    def _load_pricing_config(self) -> Dict[str, Dict[str, Any]]:
        """Load pricing configuration for all extractors"""
        return {
            # Free libraries - cost is always 0
            "PyPDF2": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.0,
                "free": True,
            },
            "PyMuPDF": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.0,
                "free": True,
            },
            "PDFPlumber": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.0,
                "free": True,
            },
            # "Camelot": {  # Disabled - causing failures
            #     "type": ExtractorType.DOCUMENT,
            #     "cost_per_page": 0.0,
            #     "free": True,
            # },
            "MarkItDown": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.0,
                "free": True,
            },
            "Tesseract": {
                "type": ExtractorType.IMAGE,
                "cost_per_image": 0.0,
                "free": True,
            },
            # Audio extractors - cost per second
            "Whisper OpenAI": {
                "type": ExtractorType.AUDIO,
                "cost_per_minute": 0.006,  # $0.006 per minute
                "cost_per_second": 0.006 / 60,
                "free": False,
            },
            "whisper-openai": {
                "type": ExtractorType.AUDIO,
                "cost_per_minute": 0.006,  # $0.006 per minute
                "cost_per_second": 0.006 / 60,
                "free": False,
            },
            "AssemblyAI": {
                "type": ExtractorType.AUDIO,
                "cost_per_second": 0.00015,  # $0.00015 per second
                "free": False,
            },
            "assemblyai": {
                "type": ExtractorType.AUDIO,
                "cost_per_second": 0.00015,  # $0.00015 per second
                "free": False,
            },
            "AWS Transcribe": {
                "type": ExtractorType.AUDIO,
                "cost_per_second": 0.00024,  # $0.00024 per second
                "free": False,
            },
            "aws-transcribe": {
                "type": ExtractorType.AUDIO,
                "cost_per_second": 0.00024,  # $0.00024 per second
                "free": False,
            },
            # Image extractors - cost per image
            "OpenAI GPT-4o Mini": {
                "type": ExtractorType.IMAGE,
                "cost_per_image": 0.01,  # ~$0.01 per image
                "free": False,
            },
            "OpenAI GPT-4o": {
                "type": ExtractorType.IMAGE,
                "cost_per_image": 0.03,  # ~$0.03 per image
                "free": False,
            },
            "OpenAI GPT-5": {
                "type": ExtractorType.IMAGE,
                "cost_per_image": 0.04,  # ~$0.04 per image
                "free": False,
            },
            "OpenAI GPT-5 Mini": {
                "type": ExtractorType.IMAGE,
                "cost_per_image": 0.015,  # ~$0.015 per image
                "free": False,
            },
            # Note: Enum values "gpt-4o-mini", "gpt-4o", "gpt-5", "gpt-5-mini" for images
            # are handled by checking usage_data type in _calculate_cost_from_config
            # They use the same pricing as the display names above
            # Note: "Mathpix" for images uses same pricing as document extraction below
            "Azure Document Intelligence": {
                "type": ExtractorType.IMAGE,
                "cost_per_1000_images": 0.10,  # $0.10 per 1000 images
                "cost_per_image": 0.0001,
                "free": False,
            },
            # Image-specific pricing for Textract (AWS Textract for images)
            "Textract Image": {
                "type": ExtractorType.IMAGE,
                "cost_per_1000_images": 1.50,  # $1.50 per 1000 images (AWS Textract Detect Document Text)
                "cost_per_image": 0.0015,
                "free": False,
            },
            # Image-specific pricing for Mathpix
            "Mathpix Image": {
                "type": ExtractorType.IMAGE,
                "cost_per_image": 0.004,  # $0.004 per image (same as per page for documents)
                "free": False,
            },
            # Document extractors - cost per page
            "LlamaParse": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.003,  # $0.003 per page
                "free": False,
            },
            "Mathpix PDF": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.004,  # $0.004 per page
                "free": False,
            },
            "Mathpix": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.004,  # $0.004 per page (same as Mathpix PDF for document extraction)
                "free": False,
            },
            "AWS Textract": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.0015,  # $0.0015 per page for Detect Text
                "free": False,
            },
            "Textract": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.0015,  # $0.0015 per page for Detect Text
                "free": False,
            },
            "Azure Document Intelligence PDF": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_1000_pages": 0.10,  # $0.10 per 1000 pages for Read
                "cost_per_page": 0.0001,
                "free": False,
            },
            "AzureDI": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_1000_pages": 0.10,  # $0.10 per 1000 pages for Read
                "cost_per_page": 0.0001,
                "free": False,
            },
            # Note: AzureDI for images uses "Azure Document Intelligence" key above
            "gpt-4o-mini": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.005,  # OpenAI GPT-4o-mini pricing per page
                "free": False,
            },
            "gpt-4o": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.010,  # OpenAI GPT-4o pricing per page
                "free": False,
            },
            "gpt-5": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.020,  # OpenAI GPT-5 pricing per page
                "free": False,
            },
            "gpt-5-mini": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.008,  # OpenAI GPT-5-mini pricing per page
                "free": False,
            },
            # "Unstructured": {  # Disabled - causing failures
            #     "type": ExtractorType.DOCUMENT,
            #     "cost_per_page": 0.001,  # Estimated
            #     "free": False,
            # },
            "Nanonets": {
                "type": ExtractorType.DOCUMENT,
                "cost_per_page": 0.005,  # Estimated
                "free": False,
            },
            # "Tabula": {  # Disabled - causing failures
            #     "type": ExtractorType.DOCUMENT,
            #     "cost_per_page": 0.0,  # Free library
            #     "free": True,
            # },
        }

    def calculate_cost(
        self,
        extractor_name: str,
        usage_data: Dict[str, Any],
        api_response: Optional[Dict[str, Any]] = None,
    ) -> CostMetrics:
        """
        Calculate cost for an extractor with verification against API response

        Args:
            extractor_name: Name of the extractor
            usage_data: Usage data (duration_seconds, image_count, page_count)
            api_response: Optional API response containing cost information

        Returns:
            CostMetrics: Calculated cost with verification data
        """
        from loguru import logger

        logger.info(f"💰 [COST CALCULATOR] Calculating cost for {extractor_name}")
        logger.info(f"💰 [COST CALCULATOR] Usage data: {usage_data}")
        logger.info(
            f"💰 [COST CALCULATOR] Has API response: {api_response is not None}"
        )

        # 1. Try to get cost from API response (most accurate)
        if api_response:
            actual_cost = self._extract_cost_from_api_response(api_response)
            if actual_cost is not None:
                return CostMetrics(
                    calculated_cost=actual_cost,
                    actual_cost=actual_cost,
                    usage_metrics=usage_data,
                    cost_source="api",
                )

        # 2. Try to get cost from Langfuse
        if self.langfuse_client:
            langfuse_cost = self._get_cost_from_langfuse(extractor_name, usage_data)
            if langfuse_cost is not None:
                return CostMetrics(
                    calculated_cost=langfuse_cost,
                    usage_metrics=usage_data,
                    cost_source="langfuse",
                )

        # 3. Fallback to configured pricing
        calculated_cost = self._calculate_cost_from_config(extractor_name, usage_data)

        return CostMetrics(
            calculated_cost=calculated_cost,
            usage_metrics=usage_data,
            cost_source="calculated",
        )

    def _extract_cost_from_api_response(
        self, api_response: Dict[str, Any]
    ) -> Optional[float]:
        """Extract cost from API response if available"""
        # Common patterns for cost in API responses
        cost_fields = [
            "cost",
            "total_cost",
            "usage",
            "pricing",
            "amount",
            "charge",
            "price",
            "total_amount",
            "cost_usd",
        ]

        for field in cost_fields:
            if field in api_response:
                cost_value = api_response[field]
                if isinstance(cost_value, (int, float)) and cost_value > 0:
                    return float(cost_value)

        # Check nested structures
        if "usage" in api_response and isinstance(api_response["usage"], dict):
            usage = api_response["usage"]
            if "cost" in usage:
                return float(usage["cost"])

        return None

    def _get_cost_from_langfuse(
        self, extractor_name: str, usage_data: Dict[str, Any]
    ) -> Optional[float]:
        """Get cost from Langfuse if available"""
        if not self.langfuse_client:
            return None

        try:
            # This would typically involve querying Langfuse API
            # For now, return None to use calculated cost
            # In a full implementation, you'd query Langfuse for model pricing
            return None
        except Exception as e:
            print(f"Error getting cost from Langfuse: {e}")
            return None

    def _calculate_cost_from_config(
        self, extractor_name: str, usage_data: Dict[str, Any]
    ) -> float:
        """Calculate cost from configuration"""
        from loguru import logger

        logger.info(
            f"💰 [COST CONFIG] Calculating cost from config for {extractor_name}"
        )

        # Determine extraction type from usage_data if available
        # This helps handle extractors that can be used for both image and document extraction
        inferred_type = None
        if "duration_seconds" in usage_data:
            inferred_type = ExtractorType.AUDIO
        elif "image_count" in usage_data:
            inferred_type = ExtractorType.IMAGE
        elif "page_count" in usage_data:
            inferred_type = ExtractorType.DOCUMENT

        # Try to get config for the extractor name
        config = self.pricing_config.get(extractor_name)

        # Check if config type matches inferred type - if not, try alternative keys
        config_type_mismatch = False
        if config and inferred_type:
            config_type = config.get("type")
            if config_type and config_type != inferred_type:
                config_type_mismatch = True
                logger.info(
                    f"💰 [COST CONFIG] Config type mismatch: config type is {config_type}, "
                    f"inferred type is {inferred_type} for {extractor_name}"
                )

        # If config not found or type mismatch, and we have an inferred type, try alternative keys
        if (not config or config_type_mismatch) and inferred_type:
            # Try alternative keys based on inferred type
            if inferred_type == ExtractorType.DOCUMENT:
                # For document extraction, try "Mathpix PDF" if extractor is "Mathpix"
                if extractor_name == "Mathpix":
                    config = self.pricing_config.get("Mathpix PDF")
                # For document extraction, try "Azure Document Intelligence PDF" if extractor is "AzureDI"
                elif extractor_name == "AzureDI":
                    config = self.pricing_config.get("Azure Document Intelligence PDF")
            elif inferred_type == ExtractorType.IMAGE:
                # For image extraction, try "Azure Document Intelligence" if extractor is "AzureDI"
                if extractor_name == "AzureDI":
                    config = self.pricing_config.get("Azure Document Intelligence")
                # For image extraction, try display names for OpenAI models
                elif extractor_name == "gpt-4o-mini":
                    config = self.pricing_config.get("OpenAI GPT-4o Mini")
                elif extractor_name == "gpt-4o":
                    config = self.pricing_config.get("OpenAI GPT-4o")
                elif extractor_name == "gpt-5":
                    config = self.pricing_config.get("OpenAI GPT-5")
                elif extractor_name == "gpt-5-mini":
                    config = self.pricing_config.get("OpenAI GPT-5 Mini")
                # For image extraction, try image-specific pricing for Textract
                elif extractor_name == "Textract":
                    config = self.pricing_config.get("Textract Image")
                # For image extraction, try image-specific pricing for Mathpix
                elif extractor_name == "Mathpix":
                    config = self.pricing_config.get("Mathpix Image")

        if not config:
            logger.warning(
                f"💰 [COST CONFIG] No config found for {extractor_name}, using default cost"
            )
            # Default cost for unknown extractors
            return 0.001

        logger.info(f"💰 [COST CONFIG] Found config: {config}")

        if config.get("free", False):
            logger.info(f"💰 [COST CONFIG] {extractor_name} is free")
            return 0.0

        # Use inferred type if available, otherwise use config type
        extractor_type = inferred_type if inferred_type else config["type"]

        if extractor_type == ExtractorType.AUDIO:
            duration_seconds = usage_data.get("duration_seconds", 0)
            cost_per_second = config.get("cost_per_second", 0)
            cost_per_minute = config.get("cost_per_minute", 0)

            logger.info(
                f"💰 [COST CONFIG] Audio extractor - duration: {duration_seconds}s, "
                f"cost_per_second: {cost_per_second}, cost_per_minute: {cost_per_minute}"
            )

            if cost_per_second > 0:
                cost = round(duration_seconds * cost_per_second, 6)
                logger.info(f"💰 [COST CONFIG] Calculated cost (per second): ${cost}")
                return cost
            elif cost_per_minute > 0:
                cost = round((duration_seconds / 60) * cost_per_minute, 6)
                logger.info(f"💰 [COST CONFIG] Calculated cost (per minute): ${cost}")
                return cost
            
            logger.warning(
                f"💰 [COST CONFIG] No valid pricing found for audio extractor {extractor_name} "
                f"(cost_per_second={cost_per_second}, cost_per_minute={cost_per_minute})"
            )
            return 0.0

        elif extractor_type == ExtractorType.IMAGE:
            image_count = usage_data.get("image_count", 1)
            cost_per_image = config.get("cost_per_image", 0)
            cost_per_1000_images = config.get("cost_per_1000_images", 0)

            logger.info(
                f"💰 [COST CONFIG] Image extractor - images: {image_count}, cost_per_image: {cost_per_image}, cost_per_1000_images: {cost_per_1000_images}"
            )

            if cost_per_image > 0:
                cost = round(image_count * cost_per_image, 6)
                logger.info(f"💰 [COST CONFIG] Calculated cost (per image): ${cost}")
                return cost
            elif cost_per_1000_images > 0:
                cost = round((image_count / 1000) * cost_per_1000_images, 6)
                logger.info(f"💰 [COST CONFIG] Calculated cost (per 1000 images): ${cost}")
                return cost

        elif extractor_type == ExtractorType.DOCUMENT:
            page_count = usage_data.get("page_count", 1)
            cost_per_page = config.get("cost_per_page", 0)
            cost_per_1000_pages = config.get("cost_per_1000_pages", 0)

            logger.info(
                f"💰 [COST CONFIG] Document extractor - pages: {page_count}, cost_per_page: {cost_per_page}, cost_per_1000_pages: {cost_per_1000_pages}"
            )

            if cost_per_page > 0:
                cost = round(page_count * cost_per_page, 6)
                logger.info(f"💰 [COST CONFIG] Calculated cost (per page): ${cost}")
                return cost
            elif cost_per_1000_pages > 0:
                cost = round((page_count / 1000) * cost_per_1000_pages, 6)
                logger.info(
                    f"💰 [COST CONFIG] Calculated cost (per 1000 pages): ${cost}"
                )
                return cost

        return 0.0

    def calculate_audio_cost(
        self, service_name: str, duration_seconds: float, **kwargs
    ) -> float:
        """
        Convenience method for audio cost calculation
        Args:
            service_name: Name of the audio service
            duration_seconds: Duration in seconds
            **kwargs: Additional parameters
        Returns:
            float: Calculated cost
        """
        usage_data = {"duration_seconds": duration_seconds, **kwargs}
        cost_metrics = self.calculate_cost(service_name, usage_data)
        return cost_metrics.calculated_cost

    def calculate_image_cost(
        self, service_name: str, image_count: int, **kwargs
    ) -> float:
        """
        Convenience method for image cost calculation
        Args:
            service_name: Name of the image service
            image_count: Number of images
            **kwargs: Additional parameters
        Returns:
            float: Calculated cost
        """
        usage_data = {"image_count": image_count, **kwargs}
        cost_metrics = self.calculate_cost(service_name, usage_data)
        return cost_metrics.calculated_cost

    def calculate_document_cost(
        self, service_name: str, page_count: int, **kwargs
    ) -> float:
        """
        Convenience method for document cost calculation
        Args:
            service_name: Name of the document service
            page_count: Number of pages
            **kwargs: Additional parameters
        Returns:
            float: Calculated cost
        """
        usage_data = {"page_count": page_count, **kwargs}
        cost_metrics = self.calculate_cost(service_name, usage_data)
        return cost_metrics.calculated_cost

    def _convert_usage_to_langfuse_format(
        self, usage_metrics: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert usage_metrics to Langfuse-compatible format"""
        if not usage_metrics:
            return None

        # Langfuse expects either:
        # {input, output, total, unit} or {promptTokens, completionTokens, totalTokens}
        
        # For document extraction: use page_count as input
        if "page_count" in usage_metrics:
            page_count = usage_metrics.get("page_count", 0)
            return {
                "input": page_count,
                "output": 0,
                "total": page_count,
                "unit": "pages",
            }
        
        # For image extraction: use image_count as input
        if "image_count" in usage_metrics:
            image_count = usage_metrics.get("image_count", 0)
            return {
                "input": image_count,
                "output": 0,
                "total": image_count,
                "unit": "images",
            }
        
        # For audio extraction: use duration_seconds as input
        if "duration_seconds" in usage_metrics:
            duration = usage_metrics.get("duration_seconds", 0)
            return {
                "input": duration,
                "output": 0,
                "total": duration,
                "unit": "seconds",
            }
        
        # If we can't convert, return None (don't pass usage)
        return None

    def track_usage(
        self,
        extractor_name: str,
        usage_data: Dict[str, Any],
        cost_metrics: CostMetrics,
        trace_id: Optional[str] = None,
    ):
        """Track usage in Langfuse for analytics"""
        if not self.langfuse_client:
            return
        try:
            # Convert usage_metrics to Langfuse format
            langfuse_usage = None
            if cost_metrics.usage_metrics:
                langfuse_usage = self._convert_usage_to_langfuse_format(
                    cost_metrics.usage_metrics
                )

            # Create a trace in Langfuse
            trace = self.langfuse_client.trace(
                name=f"{extractor_name}_extraction",
                id=trace_id,
                input=usage_data,
                metadata={
                    "extractor": extractor_name,
                    "cost_source": cost_metrics.cost_source,
                    "calculated_cost": cost_metrics.calculated_cost,
                    "stage": STAGE,
                },
            )
            # Add usage generation if we have valid Langfuse usage format
            if langfuse_usage:
                trace.generation(
                    name=f"{extractor_name}_generation",
                    usage=langfuse_usage,
                    cost=cost_metrics.calculated_cost,
                )
        except Exception as e:
            from loguru import logger
            logger.error(f"Error tracking usage in Langfuse: {e}")


# Global instance
cost_calculator = CostCalculator()
