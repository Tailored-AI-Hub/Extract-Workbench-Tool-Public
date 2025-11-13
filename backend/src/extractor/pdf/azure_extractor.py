import os
import json
import logging
from typing import Dict, Any, Union, Optional
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from .interface import PDFExtractorInterface
from src.constants import AZURE_DI_ENDPOINT, AZURE_DI_KEY
import fitz  # PyMuPDF for image extraction
import aioboto3
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method

logger = logging.getLogger(__name__)


class AzureDIExtractor(PDFExtractorInterface):
    """
    Azure Document Intelligence extractor for PDF processing.
    Uses sections-based ordering for natural reading flow.
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
            "description": "Extracts text, tables, figures, and document structure from PDFs using Azure Document Intelligence service.",
            "credentials_configured": bool(self._endpoint and self._api_key and self._client)
        }
        return info
    
    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Extract content from PDF using Azure Document Intelligence.
        
        Args:
            file_path: Path to the PDF file
            **kwargs: Additional options
        
        Returns:
            Dictionary mapping page numbers to extracted content
        """
        if not self._client:
            logger.error("Azure DI client not initialized. Check credentials.")
            return {
                1: {
                    "content": {"TEXT": ""},
                    "metadata": {"error": "Azure DI client not initialized"}
                }
            }
        
        if not os.path.isfile(file_path):
            logger.error(f"Invalid file path: {file_path}")
            return {
                1: {
                    "content": {"TEXT": ""},
                    "metadata": {"error": f"Invalid file path for Azure DI: {file_path}"}
                }
            }
        
        try:
            logger.info(f"Starting Azure DI extraction for: {file_path}")
            
            # Read PDF file
            with open(file_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            
            # Analyze document with Azure DI
            poller = self._client.begin_analyze_document(
                "prebuilt-layout",
                body=pdf_bytes,
                content_type="application/pdf",
            )
            
            result = poller.result()
            
            # Process the result into structured format
            # Pass pdf_bytes and document_uuid for figure extraction
            kwargs['pdf_bytes'] = pdf_bytes
            kwargs['document_uuid'] = kwargs.get('document_uuid', 'unknown')
            page_contents = self._process_azure_result_with_sections(result, file_path, **kwargs)
            
            self._last_result = page_contents
            
            # Log summary only (not full content)
            total_pages = len(page_contents)
            total_tables = sum(1 for page_data in page_contents.values() 
                             if page_data.get("content", {}).get("TABLES"))
            total_figures = sum(len(page_data.get("content", {}).get("IMAGES", []))
                              for page_data in page_contents.values())
            logger.info(f"Azure DI extraction: {total_pages} pages, {total_tables} tables, {total_figures} figures")
            logger.info(f"Azure DI extraction completed for {file_path}")
            return page_contents
            
        except Exception as e:
            logger.error(f"Azure DI extraction failed for {file_path}: {e}")
            return {
                1: {
                    "content": {
                        "TEXT": "",
                        "TABLES": "",
                        "MARKDOWN": "",
                        "FIGURES": "",
                        "COMBINED": ""
                    },
                    "metadata": {"error": str(e)}
                }
            }
    
    def _process_azure_result_with_sections(self, result, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Process Azure DI result using sections-based ordering.
        Sections provide natural reading flow with correct positioning of tables and figures.
        """
        page_contents = {}
        
        try:
            # Convert result to dictionary
            if hasattr(result, 'as_dict'):
                result_dict = result.as_dict()
            else:
                result_dict = result.to_dict()
            
            # Extract tables and figures at document level
            tables = self._extract_tables(result_dict)
            
            # Extract figures with S3 upload
            pdf_bytes = kwargs.get('pdf_bytes')
            document_uuid = kwargs.get('document_uuid', 'unknown')
            if pdf_bytes:
                try:
                    # Run async figure extraction with S3 upload
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If already in an event loop, create a new one in a thread
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self._extract_figures(result_dict, pdf_bytes, document_uuid))
                            figures = future.result()
                    else:
                        figures = asyncio.run(self._extract_figures(result_dict, pdf_bytes, document_uuid))
                except Exception as e:
                    logger.warning(f"Figure extraction with S3 upload failed: {e}")
                    figures = []
            else:
                figures = []
            
            # Get sections for natural ordering
            sections = getattr(result, "sections", []) or []
            paragraphs = getattr(result, "paragraphs", []) or []
            
            # Group content by page based on sections - maintain order
            pages_dict = {}
            
            # Process sections to maintain natural flow
            if sections:
                for section_idx, section in enumerate(sections):
                    elements = getattr(section, "elements", None) or []
                    
                    # Group elements by page, maintaining order
                    elements_by_page = {}
                    
                    for elem in elements:
                        if isinstance(elem, str):
                            if elem.startswith("/paragraphs/"):
                                # Extract paragraph
                                try:
                                    para_idx = int(elem.split("/")[-1])
                                    if para_idx < len(paragraphs):
                                        para = paragraphs[para_idx]
                                        content = (getattr(para, "content", None) or "").strip()
                                        if content:
                                            page_num = self._get_page_number(para)
                                            if page_num:
                                                if page_num not in elements_by_page:
                                                    elements_by_page[page_num] = []
                                                elements_by_page[page_num].append({
                                                    "type": "paragraph",
                                                    "content": content
                                                })
                                except (ValueError, IndexError):
                                    continue
                            
                            elif elem.startswith("/tables/"):
                                # Extract table
                                try:
                                    table_idx = int(elem.split("/")[-1])
                                    if table_idx < len(tables):
                                        table = tables[table_idx]
                                        page_num = table.get("page")
                                        if page_num:
                                            if page_num not in elements_by_page:
                                                elements_by_page[page_num] = []
                                            elements_by_page[page_num].append({
                                                "type": "table",
                                                "content": table
                                            })
                                except (ValueError, IndexError):
                                    continue
                            
                            elif elem.startswith("/figures/"):
                                # Extract figure
                                try:
                                    fig_idx = int(elem.split("/")[-1])
                                    if fig_idx < len(figures):
                                        figure = figures[fig_idx]
                                        page_num = figure.get("page")
                                        if page_num:
                                            if page_num not in elements_by_page:
                                                elements_by_page[page_num] = []
                                            elements_by_page[page_num].append({
                                                "type": "figure",
                                                "content": figure
                                            })
                                except (ValueError, IndexError):
                                    continue
                    
                    # Build content for each page, preserving order
                    for page_num, ordered_elements in elements_by_page.items():
                        if page_num not in pages_dict:
                            pages_dict[page_num] = {
                                "ordered_elements": []
                            }
                        
                        pages_dict[page_num]["ordered_elements"].extend(ordered_elements)
            
            # If no sections, fall back to pages-based extraction
            if not pages_dict:
                pages = result_dict.get('pages', [])
                for page_data in pages:
                    page_number = page_data.get('pageNumber', 1)
                    if page_number not in pages_dict:
                        pages_dict[page_number] = {
                            "text": [],
                            "tables": [],
                            "markdown": [],
                            "figures": [],
                        }
                    
                    # Extract text from lines
                    lines = page_data.get('lines', [])
                    for line in lines:
                        content = line.get('content', '').strip()
                        if content:
                            pages_dict[page_number]["text"].append(content)
                    
                    # Add tables for this page
                    page_tables = [t for t in tables if t.get('page') == page_number]
                    for table in page_tables:
                        pages_dict[page_number]["tables"].append(table)
                    
                    # Add figures for this page
                    page_figures = [f for f in figures if f.get('page') == page_number]
                    for figure in page_figures:
                        pages_dict[page_number]["figures"].append(figure)
            
            # Build final output with proper ordering
            for page_num, page_data in sorted(pages_dict.items()):
                # Check if we have ordered elements (sections mode)
                if "ordered_elements" in page_data:
                    ordered_elements = page_data["ordered_elements"]
                    
                    # Build content in sections order
                    text_parts = []
                    table_texts = []
                    table_markdowns = []
                    figures_list = []
                    combined_parts = []
                    markdown_parts = []
                    image_counter = 0
                    
                    for element in ordered_elements:
                        if element["type"] == "paragraph":
                            text_parts.append(element["content"])
                            combined_parts.append(element["content"])
                            markdown_parts.append(element["content"])
                        elif element["type"] == "table":
                            table = element["content"]
                            if table.get('text'):
                                table_texts.append(table['text'])
                            if table.get('markdown'):
                                table_markdowns.append(table['markdown'])
                                combined_parts.append(f"\n\n{table['markdown']}\n\n")
                                markdown_parts.append(table['markdown'])
                            elif table.get('text'):
                                combined_parts.append(f"\n\nTABLE:\n{table['text']}\n\n")
                                markdown_parts.append(table['text'])
                        elif element["type"] == "figure":
                            figure = element["content"]
                            image_counter += 1
                            combined_parts.append(f"[IMAGE_{image_counter}]")
                            figures_list.append({
                                "order": image_counter,
                                "text": figure.get('text'),
                                "caption": figure.get('caption'),
                                "page": figure.get('page'),
                                "bbox": figure.get('bbox') or {},
                                "confidence": figure.get('confidence'),
                                "image_url": figure.get('image_url') or '',
                                "image_width": figure.get('image_width') or 0,
                                "image_height": figure.get('image_height') or 0,
                            })
                    
                    text_content = "\n".join(text_parts).strip()
                    # Expose TABLES as markdown for valid rendering
                    table_content = "\n\n".join(table_markdowns) if table_markdowns else ""
                    markdown_content = "\n\n".join(markdown_parts).strip()
                    figure_content = figures_list
                    combined_content = "\n".join(combined_parts).strip()
                else:
                    # Fallback for non-sections mode
                    content_items = page_data
                    text_content = "\n".join(content_items.get("text", [])).strip()
                    
                    table_texts = []
                    table_markdowns = []
                    for table in content_items.get("tables", []):
                        if table.get('text'):
                            table_texts.append(table['text'])
                        if table.get('markdown'):
                            table_markdowns.append(table['markdown'])
                    
                    # Expose TABLES as markdown for valid rendering
                    table_content = "\n\n".join(table_markdowns) if table_markdowns else ""
                    markdown_content = "\n\n".join(table_markdowns) if table_markdowns else ""
                    
                    figures = content_items.get("figures", [])
                    figures_list = []
                    for idx, figure in enumerate[Any](figures, start=1):
                        figures_list.append({
                            "order": idx,
                            "text": figure.get('text'),
                            "caption": figure.get('caption'),
                            "page": figure.get('page'),
                            "bbox": figure.get('bbox') or {},
                            "confidence": figure.get('confidence'),
                            "image_url": figure.get('image_url') or '',
                            "image_width": figure.get('image_width') or 0,
                            "image_height": figure.get('image_height') or 0,
                        })
                    figure_content = figures_list
                    
                    # In fallback, we cannot determine precise order; append image placeholders after tables
                    if figures_list:
                        image_placeholders = "\n".join([f"[IMAGE_{f['order']}]" for f in figures_list])
                        combined_content = f"{text_content}\n\n{table_content}\n\n{image_placeholders}".strip()
                    else:
                        combined_content = f"{text_content}\n\n{table_content}".strip()
                
                # Format output with uppercase keys
                formatted_content = {
                    "TEXT": text_content,
                    "TABLES": table_content,
                    "MARKDOWN": markdown_content,
                    "IMAGES": figure_content,
                    "COMBINED": combined_content
                }


                # Get counts for metadata
                if "ordered_elements" in page_data:
                    tables_count = sum(1 for e in page_data["ordered_elements"] if e["type"] == "table")
                    figures_count = sum(1 for e in page_data["ordered_elements"] if e["type"] == "figure")
                else:
                    tables_count = len(page_data.get("tables", []))
                    figures_count = len(page_data.get("figures", []))
                
                page_contents[page_num] = {
                    "content": formatted_content,
                    "metadata": {
                        "extractor": "Azure Document Intelligence",
                        "page_number": page_num,
                        "file_path": file_path,
                        "tables_count": tables_count,
                        "figures_count": figures_count
                    }
                }
            
            # If no pages found, create a single page entry
            if not page_contents:
                page_contents[1] = {
                    "content": {
                        "TEXT": "",
                        "TABLES": "",
                        "MARKDOWN": "",
                        "IMAGES": "",
                        "COMBINED": ""
                    },
                    "metadata": {
                        "extractor": "Azure Document Intelligence",
                        "page_number": 1,
                        "file_path": file_path,
                        "error": "No page data found in Azure DI result"
                    }
                }
            
            # Log summary
            logger.info(f"Azure DI extraction: {len(page_contents)} pages, {len(tables)} tables, {len(figures)} figures")
            
        except Exception as e:
            logger.error(f"Error processing Azure DI result: {e}")
            page_contents = {
                1: {
                    "content": {
                        "TEXT": "",
                        "TABLES": "",
                        "MARKDOWN": "",
                        "IMAGES": "",
                        "COMBINED": ""
                    },
                    "metadata": {"error": f"Error processing Azure DI result: {e}"}
                }
            }
        
        return page_contents
    
    def _get_page_number(self, element) -> Optional[int]:
        """Extract page number from an element's bounding regions."""
        bounding_regions = getattr(element, "bounding_regions", None) or getattr(element, "boundingRegions", None) or []
        if bounding_regions:
            br = bounding_regions[0]
            page_num = getattr(br, "page_number", None) or getattr(br, "pageNumber", None)
            return int(page_num) if page_num else None
        return None
    
    async def _upload_image_to_s3(self, image_bytes: bytes, document_uuid: str, figure_index: int, page: int) -> str:
        """
        Upload image to S3 and return the URL.
        
        Args:
            image_bytes: Image data as bytes
            document_uuid: Document UUID for S3 key
            figure_index: Index of the figure
            page: Page number
            
        Returns:
            S3 URL of the uploaded image
        """
        try:
            # Generate S3 key
            s3_key = f"ImagesFromPDFs/{document_uuid}/images/page_{page}_figure_{figure_index}.png"
            
            # Upload to S3
            session = aioboto3.Session()
            async with session.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1")) as s3:
                await s3.put_object(
                    Bucket=os.getenv("AWS_BUCKET_NAME", "pdf-extractor-uploads"),
                    Key=s3_key,
                    Body=image_bytes,
                    ContentType="image/png"
                )
            
            # Return S3 URL
            bucket_name = os.getenv("AWS_BUCKET_NAME", "pdf-extractor-uploads")
            region = os.getenv("AWS_REGION", "us-east-1")
            s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
            
            logger.info(f"Image uploaded to S3: {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"Failed to upload image to S3: {str(e)}")
            return ""

    def _extract_image_from_pdf(self, pdf_bytes: bytes, bbox: Dict, page: int, dpi: int = 200) -> bytes:
        """
        Extract image region from PDF bytes using normalized bbox coordinates.
        Bbox keys: Left, Top, Width, Height in [0,1].
        Returns PNG image bytes.
        """
        try:
            if not pdf_bytes or not bbox:
                print(f"   🔍 Debug: No pdf_bytes or bbox provided")
                return b""
            
            # Get bbox values
            l = float(bbox.get("Left", 0.0))
            t = float(bbox.get("Top", 0.0))
            w = float(bbox.get("Width", 0.0))
            h = float(bbox.get("Height", 0.0))
            
            print(f"   🔍 Debug: Original bbox - Left: {l:.4f}, Top: {t:.4f}, Width: {w:.4f}, Height: {h:.4f}")
            
            # Validate bbox dimensions
            if w <= 0.0 or h <= 0.0:
                print(f"   ⚠️  Invalid bbox dimensions: width={w}, height={h}")
                return b""
            
            # Expand bbox by 10% margin on all sides
            margin_x = 0.10 * w
            margin_y = 0.10 * h
            l = max(0.0, l - margin_x)
            t = max(0.0, t - margin_y)
            r = min(1.0, (l + w) + margin_x * 2)
            b = min(1.0, (t + h) + margin_y * 2)
            w = max(0.0, r - l)
            h = max(0.0, b - t)
            
            print(f"   🔍 Debug: Expanded bbox - Left: {l:.4f}, Top: {t:.4f}, Width: {w:.4f}, Height: {h:.4f}")
            
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                page_number = max(1, int(page or 1))
                if page_number < 1 or page_number > len(doc):
                    print(f"   ⚠️  Invalid page number: {page_number} (total pages: {len(doc)})")
                    return b""
                
                pg = doc[page_number - 1]
                page_rect = pg.rect
                
                print(f"   🔍 Debug: Page size - width: {page_rect.width:.2f}, height: {page_rect.height:.2f}")
                
                # Convert normalized bbox to page coordinates
                x0 = page_rect.x0 + l * page_rect.width
                y0 = page_rect.y0 + t * page_rect.height
                x1 = x0 + w * page_rect.width
                y1 = y0 + h * page_rect.height
                
                print(f"   🔍 Debug: Page coords - x0: {x0:.2f}, y0: {y0:.2f}, x1: {x1:.2f}, y1: {y1:.2f}")
                
                rect = fitz.Rect(x0, y0, x1, y1)
                
                # Clip to page bounds
                rect = rect & pg.rect
                
                print(f"   🔍 Debug: Clipped rect - {rect.width:.2f} x {rect.height:.2f}")
                
                # Ensure minimum dimensions (at least 10x10 pixels)
                min_dimension = 10.0
                if rect.width < min_dimension or rect.height < min_dimension:
                    print(f"   ⚠️  Rect too small after clipping: {rect.width:.2f} x {rect.height:.2f}")
                    # Try to expand the rect slightly
                    center_x = (rect.x0 + rect.x1) / 2
                    center_y = (rect.y0 + rect.y1) / 2
                    half_size = max(min_dimension / 2, rect.width / 2, rect.height / 2)
                    rect = fitz.Rect(
                        max(page_rect.x0, center_x - half_size),
                        max(page_rect.y0, center_y - half_size),
                        min(page_rect.x1, center_x + half_size),
                        min(page_rect.y1, center_y + half_size)
                    )
                    print(f"   🔧 Adjusted rect to: {rect.width:.2f} x {rect.height:.2f}")
                
                # Validate final rect
                if not rect.is_valid or rect.is_empty:
                    print(f"   ⚠️  Invalid or empty rect after adjustments")
                    return b""
                
                # Render clipped region
                print(f"   🎨 Rendering pixmap at {dpi} DPI...")
                pix = pg.get_pixmap(clip=rect, dpi=dpi)
                image_bytes = pix.tobytes("png")
                print(f"   ✅ Image extracted: {len(image_bytes)} bytes ({pix.width}x{pix.height} pixels)")
                return image_bytes
            finally:
                doc.close()
        except Exception as e:
            print(f"   ❌ Image extraction error: {e}")
            logger.error(f"Image extraction failed: {e}")
            return b""
    
    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """Get processing status. Always 'succeeded' for sync implementation."""
        return "succeeded"
    
    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """Get the result of processing."""
        return self._last_result or {}
    
    @log_extractor_method()
    def supports_webhook(self) -> bool:
        """Azure DI doesn't use webhooks."""
        return False
    
    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """Handle webhook payload. Not supported for Azure DI."""
        raise NotImplementedError("Azure DI does not support webhooks")
    
    def _extract_tables(self, result_dict: dict) -> list:
        """Extract tables from Azure DI result."""
        tables = []
        try:
            azure_tables = result_dict.get('tables', [])
            
            for i, table in enumerate(azure_tables):
                # Get page number from bounding regions
                page_number = None
                bbox = {}
                bounding_regions = table.get('boundingRegions', [])
                if bounding_regions:
                    region = bounding_regions[0]
                    page_number = region.get('pageNumber', 1)
                    polygon = region.get('polygon', [])
                    if polygon:
                        xs = []
                        ys = []
                        for p in polygon:
                            if isinstance(p, dict):
                                xs.append(p.get('x', 0))
                                ys.append(p.get('y', 0))
                            elif isinstance(p, (list, tuple)) and len(p) >= 2:
                                xs.append(p[0])
                                ys.append(p[1])
                        
                        bbox = {
                            "Left": min(xs) if xs else 0,
                            "Top": min(ys) if ys else 0,
                            "Width": (max(xs) - min(xs)) if xs else 0,
                            "Height": (max(ys) - min(ys)) if ys else 0
                        }
                
                table_data = {
                    "text": "",
                    "markdown": "",
                    "page": page_number,
                    "bbox": bbox,
                    "confidence": table.get('confidence'),
                    "cells": table.get('cells', [])
                }
                
                # Extract table content
                cells = table.get('cells', [])
                if cells:
                    cell_data = {}
                    max_row = 0
                    max_col = 0
                    
                    for cell in cells:
                        try:
                            if not isinstance(cell, dict):
                                continue
                                
                            row_idx = int(cell.get('rowIndex', 0))
                            col_idx = int(cell.get('columnIndex', 0))
                            content = cell.get('content', '').strip()
                            
                            max_row = max(max_row, row_idx)
                            max_col = max(max_col, col_idx)
                            
                            if row_idx not in cell_data:
                                cell_data[row_idx] = {}
                            cell_data[row_idx][col_idx] = content
                        except Exception:
                            continue
                    
                    # Build markdown table
                    markdown_rows = []
                    
                    for row in range(max_row + 1):
                        row_cells = []
                        for col in range(max_col + 1):
                            content = cell_data.get(row, {}).get(col, '')
                            content = content.replace('|', '\\|').replace('\n', ' ').strip()
                            row_cells.append(content)
                        
                        markdown_rows.append("| " + " | ".join(row_cells) + " |")
                        
                        if row == 0:
                            separator = "| " + " | ".join(["---"] * (max_col + 1)) + " |"
                            markdown_rows.append(separator)
                    
                    table_data["markdown"] = "\n".join(markdown_rows)
                    
                    # Build plain text
                    table_text_rows = []
                    for row in range(max_row + 1):
                        row_cells = []
                        for col in range(max_col + 1):
                            content = cell_data.get(row, {}).get(col, '')
                            row_cells.append(content)
                        table_text_rows.append(" | ".join(row_cells))
                    
                    table_data["text"] = "\n".join(table_text_rows)
                
                tables.append(table_data)
                
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
        
        return tables
    
    async def _extract_figures(self, result_dict: dict, pdf_bytes: bytes, document_uuid: str) -> list:
        """Extract figures from Azure DI result, upload images to S3, and return metadata."""
        figures = []
        try:
            azure_figures = result_dict.get('figures', [])
            
            # Get page dimensions for normalization
            page_dims = {}
            pages = result_dict.get('pages', [])
            for page in pages:
                page_num = page.get('pageNumber')
                if page_num:
                    page_dims[page_num] = {
                        'width': page.get('width'),
                        'height': page.get('height')
                    }
            
            logger.info(f"Found {len(azure_figures)} figures in Azure DI result")
            
            for i, figure in enumerate(azure_figures):
                logger.info(f"Processing figure {i+1}")
                
                page_number = None
                bbox = {}
                image_url = ""
                image_width = 0
                image_height = 0
                bounding_regions = figure.get('boundingRegions', [])
                
                if bounding_regions:
                    region = bounding_regions[0]
                    page_number = region.get('pageNumber', 1)
                    polygon = region.get('polygon', [])
                    
                    # Get page dimensions for normalization
                    page_width = page_dims.get(page_number, {}).get('width')
                    page_height = page_dims.get(page_number, {}).get('height')
                    
                    if polygon and page_width and page_height:
                        # Parse polygon coordinates
                        xs_abs = []
                        ys_abs = []
                        
                        # Handle flat array format [x1, y1, x2, y2, ...]
                        if all(isinstance(p, (int, float)) for p in polygon):
                            for j in range(0, len(polygon), 2):
                                if j + 1 < len(polygon):
                                    xs_abs.append(float(polygon[j]))
                                    ys_abs.append(float(polygon[j + 1]))
                        # Handle dict format [{'x': ..., 'y': ...}, ...]
                        elif polygon and isinstance(polygon[0], dict):
                            for p in polygon:
                                x = p.get('x', p.get('X', 0))
                                y = p.get('y', p.get('Y', 0))
                                xs_abs.append(float(x))
                                ys_abs.append(float(y))
                        
                        if xs_abs and ys_abs:
                            # Normalize coordinates to [0, 1] range
                            xs_norm = [x / page_width for x in xs_abs]
                            ys_norm = [y / page_height for y in ys_abs]
                            
                            bbox = {
                                "Left": min(xs_norm),
                                "Top": min(ys_norm),
                                "Width": max(xs_norm) - min(xs_norm),
                                "Height": max(ys_norm) - min(ys_norm)
                            }
                            
                            # Extract image from PDF
                            try:
                                image_bytes = self._extract_image_from_pdf(pdf_bytes, bbox, page_number)
                                if image_bytes:
                                    # Upload to S3
                                    image_url = await self._upload_image_to_s3(image_bytes, document_uuid, i, page_number)
                                    
                                    # Get image dimensions
                                    import io
                                    from PIL import Image
                                    img = Image.open(io.BytesIO(image_bytes))
                                    image_width = img.width
                                    image_height = img.height
                                    
                                    logger.info(f"Figure {i+1} image extracted: {image_width}x{image_height}, URL: {image_url}")
                                else:
                                    logger.warning(f"Figure {i+1} failed to extract image")
                            except Exception as e:
                                logger.error(f"Figure {i+1} image extraction failed: {str(e)}")
                
                # Extract caption
                caption_content = ""
                caption = figure.get('caption')
                if caption:
                    caption_content = caption.get('content', '').strip()
                
                figure_data = {
                    "text": f"[Figure: {caption_content}]" if caption_content else "[Figure]",
                    "caption": caption_content,
                    "page": page_number,
                    "bbox": bbox,
                    "confidence": figure.get('confidence'),
                    "image_url": image_url,
                    "image_width": image_width,
                    "image_height": image_height,
                }
                figures.append(figure_data)
                
        except Exception as e:
            logger.error(f"Error extracting figures: {e}")
        
        return figures

    @log_extractor_method()
    def calculate_cost(self, page_count: int, **kwargs) -> float:
        """
        Calculate cost for Azure Document Intelligence based on page count.
        """
        return self.cost_calculator.calculate_document_cost(
            service_name="azure-di",
            page_count=page_count,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for Azure Document Intelligence.
        """
        try:
            # Get page count from PDF
            doc = fitz.open(file_path)
            page_count = doc.page_count
            doc.close()
            
            return {
                "page_count": page_count,
                "service": "azure-di",
                "estimated_cost": self.calculate_cost(page_count, **kwargs)
            }
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return {
                "page_count": 0,
                "service": "azure-di",
                "estimated_cost": 0.0
            }