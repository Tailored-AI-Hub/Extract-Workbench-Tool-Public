import os
import json
import logging
from typing import Dict, Any, Union
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from .interface import ImageExtractorInterface
from src.constants import AZURE_DI_ENDPOINT, AZURE_DI_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method

logger = logging.getLogger(__name__)


class AzureDIImageExtractor(ImageExtractorInterface):
    """
    Azure Document Intelligence extractor for image processing.
    """
    
    def __init__(self):
        """
        Initialize Azure Document Intelligence client.
        """
        self._last_result = None
        self._client = None
                
        # Initialize Azure DI credentials
        self._endpoint = AZURE_DI_ENDPOINT
        self._api_key = AZURE_DI_KEY
        
        if self._endpoint and self._api_key:
            try:
                self._client = DocumentIntelligenceClient(
                    endpoint=self._endpoint,
                    credential=AzureKeyCredential(self._api_key)
                )
                logger.info("Azure Document Intelligence client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Azure DI client: {e}")
                self._client = None
        else:
            logger.warning("Azure DI credentials not found. Set AZURE_DI_ENDPOINT and AZURE_DI_KEY environment variables.")
        
        self.cost_calculator = CostCalculator()
    
    @log_extractor_method()
    def get_information(self) -> dict:
        """Get information about the Azure DI extractor."""
        info = {
            "name": "Azure Document Intelligence",
            "type": "sync",
            "supports": ["text", "tables", "figures", "structure"],
            "description": "Extracts text, tables, figures, and document structure from images using Azure Document Intelligence service.",
            "credentials_configured": bool(self._endpoint and self._api_key and self._client)
        }
        return info
    
    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> dict:
        """
        Extract content from image using Azure Document Intelligence.
        
        Args:
            file_path: Path to the image file
            **kwargs: Additional options
        
        Returns:
            Dictionary with 'content' and 'metadata' keys
        """
        if not self._client:
            logger.error("Azure DI client not initialized. Check credentials.")
            return {
                "content": {"TEXT": ""},
                "metadata": {"error": "Azure DI client not initialized"}
            }
        
        if not os.path.isfile(file_path):
            logger.error(f"Invalid file path: {file_path}")
            return {
                "content": {"TEXT": ""},
                "metadata": {"error": f"Invalid file path for Azure DI: {file_path}"}
            }
        
        try:
            logger.info(f"Starting Azure DI extraction for image: {file_path}")
            
            # Determine content type based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.tiff': 'image/tiff',
                '.tif': 'image/tiff',
            }
            content_type = content_type_map.get(ext, 'image/jpeg')
            
            # Read image file
            with open(file_path, "rb") as image_file:
                image_bytes = image_file.read()
            
            # Analyze document with Azure DI
            poller = self._client.begin_analyze_document(
                "prebuilt-layout",
                body=image_bytes,
                content_type=content_type,
            )
            
            result = poller.result()
            
            # Process the result
            content_dict = self._process_azure_result(result)
            
            result_dict = {
                "content": content_dict,
                "metadata": {
                    "extractor": "Azure Document Intelligence",
                    "model": "prebuilt-layout"
                }
            }
            
            self._last_result = result_dict
            logger.info(f"Azure DI extraction completed for {file_path}")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Azure DI extraction failed for {file_path}: {e}")
            return {
                "content": {
                    "TEXT": "",
                    "TABLES": "",
                    "MARKDOWN": "",
                    "FIGURES": "",
                    "COMBINED": ""
                },
                "metadata": {"error": str(e)}
            }
    
    def _process_azure_result(self, result) -> Dict[str, Any]:
        """
        Process Azure DI result for a single image.
        Returns content dictionary with TEXT, TABLES, MARKDOWN, FIGURES, COMBINED.
        """
        content = {
            "TEXT": "",
            "TABLES": "",
            "MARKDOWN": "",
            "FIGURES": "",
            "COMBINED": ""
        }
        
        try:
            # Convert result to dictionary
            if hasattr(result, 'as_dict'):
                result_dict = result.as_dict()
            else:
                result_dict = result.to_dict()
            
            # Extract text from paragraphs
            paragraphs = getattr(result, "paragraphs", []) or []
            text_lines = []
            for para in paragraphs:
                para_content = (getattr(para, "content", None) or "").strip()
                if para_content:
                    text_lines.append(para_content)
            
            text_content = "\n".join(text_lines)
            content["TEXT"] = text_content
            
            # Extract tables
            tables = self._extract_tables(result_dict)
            if tables:
                table_content = "\n\n".join([t.get("markdown", "") for t in tables if t.get("markdown")])
                content["TABLES"] = table_content
                content["MARKDOWN"] = table_content
            
            # Extract figures (images within the document)
            figures = getattr(result, "figures", []) or []
            if figures:
                figure_list = []
                for i, fig in enumerate(figures):
                    figure_list.append({
                        "order": i + 1,
                        "page": 1,  # Single image, so page is always 1
                    })
                content["FIGURES"] = json.dumps(figure_list)
            
            # Build combined content
            combined_parts = []
            if text_content:
                combined_parts.append(text_content)
            if content["TABLES"]:
                combined_parts.append(content["TABLES"])
            if figures:
                image_placeholders = "\n".join([f"[IMAGE_{i+1}]" for i in range(len(figures))])
                combined_parts.append(image_placeholders)
            
            content["COMBINED"] = "\n\n".join(combined_parts).strip()
            
        except Exception as e:
            logger.error(f"Error processing Azure DI result: {e}")
            content["TEXT"] = f"Error processing result: {str(e)}"
        
        return content
    
    def _extract_tables(self, result_dict: dict) -> list:
        """Extract tables from Azure DI result."""
        tables = []
        try:
            azure_tables = result_dict.get('tables', [])
            for table_idx, table in enumerate(azure_tables):
                rows = table.get('rows', [])
                if not rows:
                    continue
                
                # Build markdown table
                markdown_rows = []
                for row in rows:
                    cells = row.get('cells', [])
                    cell_texts = []
                    for cell in cells:
                        content = cell.get('content', '').strip()
                        cell_texts.append(content)
                    markdown_rows.append("| " + " | ".join(cell_texts) + " |")
                
                if markdown_rows:
                    # Add header separator
                    if len(markdown_rows) > 0:
                        header_sep = "| " + " | ".join(["---"] * len(markdown_rows[0].split("|"))[1:-1]) + " |"
                        markdown_rows.insert(1, header_sep)
                    
                    table_markdown = "\n".join(markdown_rows)
                    tables.append({
                        "page": 1,  # Single image
                        "markdown": table_markdown,
                        "row_count": len(rows),
                        "column_count": len(rows[0].get('cells', [])) if rows else 0
                    })
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
        
        return tables

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Azure DI image processing is synchronous; always returns 'succeeded'.
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
        Azure DI does not support webhooks for image processing.
        """
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Webhook handling not supported for Azure DI.
        """
        raise NotImplementedError("Azure DI does not support webhooks")

    @log_extractor_method()
    def calculate_cost(self, image_count: int, **kwargs) -> float:
        """
        Calculate cost for Azure Document Intelligence based on image count.
        """
        return self.cost_calculator.calculate_image_cost(
            service_name="azure-di",
            image_count=image_count,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for Azure Document Intelligence.
        """
        return {
            "image_count": 1,
            "service": "azure-di",
            "estimated_cost": self.calculate_cost(1, **kwargs)
        }

