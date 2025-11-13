# src/extractors/textract_extractor.py
import os
import uuid
import time
from loguru import logger
from typing import Dict, Optional
from botocore.session import get_session
from .interface import PDFExtractorInterface
from src.constants import AWS_BUCKET_NAME, AWS_REGION
from ..logger_decorator import log_extractor_method

class TextractExtractor(PDFExtractorInterface):
    def __init__(self) -> None:
        self.region = AWS_REGION or os.getenv("AWS_REGION") or "us-east-1"
        self._session = None
        self._textract = None
        self._s3 = None
        self._last_result = None

    def _ensure_clients(self) -> None:
        if self._session is None:
            self._session = get_session()  # picks up env/instance creds
        if self._textract is None:
            self._textract = self._session.create_client("textract", region_name=self.region)
        if self._s3 is None:
            self._s3 = self._session.create_client("s3", region_name=self.region)

    @log_extractor_method()
    def get_information(self) -> dict:
        return {"name": "AWS Textract", "supports": ["Text", "Table"], "mode": "sync-wrapper"}

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> dict:
        return {}

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, dict]:
        self._ensure_clients()
        # Textract document extractor only handles PDFs
        bucket = AWS_BUCKET_NAME or os.getenv("AWS_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("AWS_BUCKET_NAME is not configured for Textract PDF processing")
        key = f"textract-tmp/{uuid.uuid4()}/{os.path.basename(file_path)}"
        try:
            with open(file_path, "rb") as f:
                self._s3.put_object(Bucket=bucket, Key=key, Body=f)
            start = self._textract.start_document_analysis(
                DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
                FeatureTypes=["TABLES", "FORMS"]
            )
            job_id = start["JobId"]
            delay = 1.5
            while True:
                res = self._textract.get_document_analysis(JobId=job_id, MaxResults=1000)
                status = res.get("JobStatus")
                if status == "SUCCEEDED":
                    blocks = res.get("Blocks", []) or []
                    next_token = res.get("NextToken")
                    while next_token:
                        page = self._textract.get_document_analysis(
                            JobId=job_id, NextToken=next_token, MaxResults=1000
                        )
                        blocks.extend(page.get("Blocks", []) or [])
                        next_token = page.get("NextToken")
                    result = self._blocks_to_pages(blocks)
                    self._last_result = result
                    return result
                if status == "FAILED":
                    raise RuntimeError(f"Textract job failed: {res.get('StatusMessage')}")
                time.sleep(delay)
                delay = min(delay * 1.5, 10.0)
        finally:
            try:
                self._s3.delete_object(Bucket=bucket, Key=key)
            except Exception:
                pass

    @staticmethod
    def _blocks_to_pages(blocks: list) -> Dict[int, dict]:
        # Create block lookup by ID
        block_map = {b.get("Id"): b for b in blocks or [] if b.get("Id")}
        
        # Extract text lines per page
        page_to_lines: Dict[int, list] = {}
        # Extract tables per page
        page_to_tables: Dict[int, list] = {}
        
        for b in blocks or []:
            page_num = int(b.get("Page", 1))
            
            if b.get("BlockType") == "LINE":
                text = (b.get("Text") or "").strip()
                if text:
                    page_to_lines.setdefault(page_num, []).append(text)
            
            elif b.get("BlockType") == "TABLE":
                # Extract table structure
                table_str = TextractExtractor._extract_table(b, block_map)
                if table_str:
                    page_to_tables.setdefault(page_num, []).append(table_str)
        
        # Combine text and tables for each page
        result = {}
        all_pages = set(page_to_lines.keys()) | set(page_to_tables.keys())
        for page_num in all_pages:
            text_content = "\n".join(page_to_lines.get(page_num, []))
            table_content = "\n\n".join(page_to_tables.get(page_num, []))
            
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
            
            result[page_num] = {"content": content}
        
        return result
    
    @staticmethod
    def _extract_table(table_block: dict, block_map: dict) -> str:
        """Extract table structure from Textract blocks and format as string."""
        try:
            # Get all cell IDs for this table
            relationships = table_block.get("Relationships", [])
            cell_ids = []
            for rel in relationships:
                if rel.get("Type") == "CHILD":
                    cell_ids.extend(rel.get("Ids", []))
            
            if not cell_ids:
                return ""
            
            # Build cell grid
            cells = {}
            max_row = 0
            max_col = 0
            
            for cell_id in cell_ids:
                cell_block = block_map.get(cell_id)
                if not cell_block or cell_block.get("BlockType") != "CELL":
                    continue
                
                row_idx = cell_block.get("RowIndex", 1) - 1  # 0-indexed
                col_idx = cell_block.get("ColumnIndex", 1) - 1  # 0-indexed
                
                # Extract text from cell
                cell_text = ""
                cell_relationships = cell_block.get("Relationships", [])
                for rel in cell_relationships:
                    if rel.get("Type") == "CHILD":
                        for word_id in rel.get("Ids", []):
                            word_block = block_map.get(word_id)
                            if word_block and word_block.get("BlockType") == "WORD":
                                word_text = word_block.get("Text", "")
                                if cell_text:
                                    cell_text += " "
                                cell_text += word_text
                
                cells[(row_idx, col_idx)] = cell_text.strip()
                max_row = max(max_row, row_idx)
                max_col = max(max_col, col_idx)
            
            if not cells:
                return ""
            
            # Build table string
            table_rows = []
            for row in range(max_row + 1):
                row_cells = []
                for col in range(max_col + 1):
                    cell_text = cells.get((row, col), "")
                    row_cells.append(cell_text)
                if any(row_cells):  # Only add non-empty rows
                    table_rows.append(" | ".join(row_cells))
            
            return "\n".join(table_rows)
        except Exception as e:
            logger.warning(f"Error extracting table: {e}")
            return ""

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> dict:
        return self._last_result or {}

    @log_extractor_method()
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for AWS Textract extraction.
        Pricing: $0.0015 per page for Document Analysis
        """
        from src.cost_calculator import CostCalculator
        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("AWS Textract", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for AWS Textract extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "AWS Textract",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }
