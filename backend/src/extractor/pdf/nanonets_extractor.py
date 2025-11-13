import requests
import time
from loguru import logger
from typing import Dict, Any, Union
from .interface import PDFExtractorInterface
from src.constants import NANONETS_API_KEY




class NanonetsExtractor(PDFExtractorInterface):
    def __init__(self, api_key: str):
        """
        Initialize Nanonets extractor with API credentials.
        """
        self.api_key = NANONETS_API_KEY
        self._last_result = None
        self.upload_endpoint = "https://app.nanonets.com/api/v2/OCR/FullText"
        self.result_endpoint = "https://app.nanonets.com/api/v2/OCR/FullText"

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "Nanonets",
            "type": "async",
            "supports": ["text", "tables", "ocr"],
            "description": "Extracts text, tables, and structured data using Nanonets OCR API."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> str:
        """
        Upload PDF to Nanonets and return request ID for async processing.
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                
                response = requests.post(
                    self.upload_endpoint,
                    auth=requests.auth.HTTPBasicAuth(self.api_key, ''),
                    files=files
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Nanonets returns request_id for tracking
            request_id = result.get('request_id') or result.get('id')
            
            if not request_id:
                raise ValueError("No request_id returned from Nanonets")
            
            logger.info(f"PDF uploaded successfully. Request ID: {request_id}")
            return request_id

        except Exception as e:
            logger.error(f"Nanonets PDF upload failed: {str(e)}")
            raise

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Check the processing status of the PDF.
        Returns: 'processing', 'succeeded', 'failed'
        """
        try:
            response = requests.get(
                f"{self.result_endpoint}/{job_id}",
                auth=requests.auth.HTTPBasicAuth(self.api_key, '')
            )
            response.raise_for_status()
            
            status_data = response.json()
            
            # Check if result is ready
            if status_data.get('message') == 'Success' or status_data.get('result'):
                return 'succeeded'
            elif status_data.get('message') == 'Processing':
                return 'processing'
            elif status_data.get('error'):
                return 'failed'
            else:
                return 'processing'

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return 'processing'
            logger.error(f"Failed to check status: {str(e)}")
            return 'failed'
        except Exception as e:
            logger.error(f"Failed to check status: {str(e)}")
            return 'failed'

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        Get the processed results from Nanonets.
        
        Returns:
            Dict with page contents in the standard format
        """
        try:
            response = requests.get(
                f"{self.result_endpoint}/{job_id}",
                auth=requests.auth.HTTPBasicAuth(self.api_key, '')
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse Nanonets response
            page_contents: Dict[int, Dict[str, Any]] = {}
            
            if data.get('result'):
                results = data['result']
                
                # Nanonets returns predictions with page information
                if isinstance(results, list):
                    for idx, result in enumerate(results, start=1):
                        page_contents[idx] = self._parse_nanonets_result(result, idx)
                else:
                    page_contents[1] = self._parse_nanonets_result(results, 1)
            
            elif data.get('predictions'):
                # Alternative response format
                predictions = data['predictions']
                
                # Group by page
                pages_data = {}
                for pred in predictions:
                    page_num = pred.get('page', 1)
                    if page_num not in pages_data:
                        pages_data[page_num] = []
                    pages_data[page_num].append(pred)
                
                for page_num, preds in pages_data.items():
                    page_contents[page_num] = self._parse_predictions(preds, page_num)
            
            else:
                # Fallback: extract raw text
                raw_text = data.get('raw_text', '')
                page_contents[1] = {
                    "content": {
                        "TEXT": raw_text,
                        "TABLES": "",
                        "OCR": raw_text
                    },
                    "metadata": {
                        "extractor": "Nanonets",
                        "request_id": job_id
                    }
                }
            
            if not page_contents:
                page_contents = {
                    1: {
                        "content": {"TEXT": "", "TABLES": "", "OCR": ""},
                        "metadata": {"error": "No content extracted"}
                    }
                }
            
            self._last_result = page_contents
            return page_contents

        except Exception as e:
            logger.error(f"Failed to get results: {str(e)}")
            return {
                1: {
                    "content": {"TEXT": "", "TABLES": "", "OCR": ""},
                    "metadata": {"error": str(e)}
                }
            }

    def _parse_nanonets_result(self, result: dict, page_num: int) -> Dict[str, Any]:
        """
        Parse a single Nanonets result into our standard format.
        """
        # Extract text from OCR results
        ocr_text = result.get('ocr_text', '')
        raw_text = result.get('raw_text', ocr_text)
        
        # Extract tables if present
        tables = result.get('tables', [])
        table_strings = []
        
        for table in tables:
            if isinstance(table, dict):
                # Format table data
                table_str = self._format_nanonets_table(table)
                table_strings.append(table_str)
            elif isinstance(table, str):
                table_strings.append(table)
        
        tables_text = "\n\n".join(table_strings)
        
        return {
            "content": {
                "TEXT": raw_text,
                "TABLES": tables_text,
                "OCR": ocr_text
            },
            "metadata": {
                "extractor": "Nanonets",
                "page_number": page_num,
                "tables_found": len(table_strings),
                "confidence": result.get('confidence')
            }
        }

    def _parse_predictions(self, predictions: list, page_num: int) -> Dict[str, Any]:
        """
        Parse Nanonets predictions format.
        """
        all_text = []
        tables = []
        
        for pred in predictions:
            label = pred.get('label', '')
            ocr_text = pred.get('ocr_text', '')
            
            if label.lower() in ['table', 'table_cell']:
                tables.append(ocr_text)
            else:
                all_text.append(ocr_text)
        
        return {
            "content": {
                "TEXT": "\n".join(all_text),
                "TABLES": "\n\n".join(tables),
                "OCR": "\n".join(all_text + tables)
            },
            "metadata": {
                "extractor": "Nanonets",
                "page_number": page_num,
                "tables_found": len(tables),
                "predictions_count": len(predictions)
            }
        }

    def _format_nanonets_table(self, table: dict) -> str:
        """
        Format a Nanonets table into a readable string.
        """
        if 'rows' in table:
            rows = table['rows']
            formatted_rows = []
            for row in rows:
                if isinstance(row, list):
                    formatted_rows.append(" | ".join(str(cell) for cell in row))
                elif isinstance(row, dict) and 'cells' in row:
                    formatted_rows.append(" | ".join(str(cell) for cell in row['cells']))
            return "\n".join(formatted_rows)
        elif 'cells' in table:
            return str(table['cells'])
        else:
            return str(table)

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        """
        Nanonets supports webhooks for async notifications.
        """
        return True

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Handle webhook payload from Nanonets.
        """
        try:
            request_id = payload.get('request_id') or payload.get('id')
            
            if not request_id:
                raise ValueError("No request_id in webhook payload")
            
            # Process the webhook result
            return self.get_result(request_id)
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {str(e)}")
            raise