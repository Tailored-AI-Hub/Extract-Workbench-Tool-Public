import requests
from typing import Union, Optional
from .interface import PDFExtractorInterface
from loguru import logger
from src.constants import LLAMAPARSE_API_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method


class LlamaParseExtractor(PDFExtractorInterface):
    def __init__(self):
        self._last_result = None
        self._job_id = None
        self.api_key = LLAMAPARSE_API_KEY
        self.base_url = "https://api.cloud.llamaindex.ai/api/v1/parsing"

    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "LlamaParse",
            "type": "async",
            "supports": ["text", "tables", "markdown"],
            "description": "Extracts text and tables from PDFs using LlamaParse API with high accuracy."
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs):
        """
        Start extraction job with LlamaParse API.
        Returns job_id for async processing.
        """
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Prepare headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            # Prepare files
            files = {
                'file': (file_path.split('/')[-1], file_content, 'application/pdf')
            }

            # Prepare data with page separation parameters
            data = {
                'page_separator': '\n---\n',  # Default page separator
                'page_prefix': 'PAGE {pageNumber}:\n',  # Add page number prefix
                'page_suffix': '\n'  # Add suffix after each page
            }

            # Start extraction job
            response = requests.post(
                f"{self.base_url}/upload",
                headers=headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            
            result = response.json()
            self._job_id = result.get('id')
            
            logger.info(f"LlamaParse job started with ID: {self._job_id}")
            return self._job_id

        except Exception as e:
            logger.error(f"LlamaParse extraction failed: {str(e)}")
            raise

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Check the status of the LlamaParse job.
        """
        if not job_id:
            return "failed"
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            response = requests.get(
                f"{self.base_url}/job/{job_id}",
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            status = result.get('status', 'unknown')
            logger.info(f"LlamaParse status for {job_id}: {status}")
            
            # Map LlamaParse status to our status
            if status == 'SUCCESS':
                return "succeeded"
            elif status == 'FAILED':
                return "failed"
            elif status in ['PENDING', 'RUNNING']:
                return "running"
            else:
                return "pending"
                
        except Exception as e:
            logger.error(f"Error checking LlamaParse status: {str(e)}")
            return "failed"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        Fetch the result from LlamaParse API and parse it by pages.
        """
        if not job_id:
            return {}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }
            
            response = requests.get(
                f"{self.base_url}/job/{job_id}/result/raw/markdown",
                headers=headers
            )
            response.raise_for_status()
            
            result = response.text
            
            # Parse the result by pages
            page_contents = self._parse_content_by_pages(result)
            
            # Store result for internal use
            self._last_result = page_contents
            
            return self._last_result
            
        except Exception as e:
            logger.error(f"Error fetching LlamaParse result: {str(e)}")
            return {}

    def _parse_content_by_pages(self, content: str) -> dict:
        """
        Parse LlamaParse content and separate it by pages.
        """
        page_contents = {}
        
        try:
            # Split content by page separators
            # Look for patterns like "PAGE X:" followed by content until next "PAGE Y:" or end
            import re
            
            # Pattern to match page headers like "PAGE 1:", "PAGE 2:", etc.
            page_pattern = r'PAGE\s+(\d+):\s*\n(.*?)(?=PAGE\s+\d+:|$)'
            matches = re.findall(page_pattern, content, re.DOTALL)
            
            if matches:
                # Content was properly separated by pages
                for page_num_str, page_content in matches:
                    page_num = int(page_num_str)
                    # Clean up the content (remove extra whitespace)
                    clean_content = page_content.strip()
                    
                    page_contents[page_num] = {
                        "content": {
                            "MARKDOWN": clean_content,
                            "TEXT": clean_content
                        },
                        "metadata": {
                            "extractor": "LlamaParse",
                            "format": "markdown",
                            "page_number": page_num,
                            "job_id": self._job_id
                        }
                    }
            else:
                # Fallback: try to split by the default separator "---"
                pages = content.split('\n---\n')
                for i, page_content in enumerate(pages, 1):
                    clean_content = page_content.strip()
                    if clean_content:  # Only add non-empty pages
                        page_contents[i] = {
                            "content": {
                                "MARKDOWN": clean_content,
                                "TEXT": clean_content
                            },
                            "metadata": {
                                "extractor": "LlamaParse",
                                "format": "markdown",
                                "page_number": i,
                                "job_id": self._job_id
                            }
                        }
            
            # If no pages were found, put everything in page 1 as fallback
            if not page_contents:
                page_contents[1] = {
                    "content": {
                        "MARKDOWN": content.strip(),
                        "TEXT": content.strip()
                    },
                    "metadata": {
                        "extractor": "LlamaParse",
                        "format": "markdown",
                        "page_number": 1,
                        "job_id": self._job_id
                    }
                }
                
        except Exception as e:
            logger.error(f"Error parsing LlamaParse content by pages: {str(e)}")
            # Fallback to single page
            page_contents[1] = {
                "content": {
                    "MARKDOWN": content.strip(),
                    "TEXT": content.strip()
                },
                "metadata": {
                    "extractor": "LlamaParse",
                    "format": "markdown",
                    "page_number": 1,
                    "job_id": self._job_id,
                    "error": str(e)
                }
            }
        
        return page_contents

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        """
        Use polling mode for now (webhook not wired in backend routes).
        """
        return False

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Process webhook payload from LlamaParse.
        """
        try:
            job_id = payload.get('job_id')
            status = payload.get('status')
            
            if status == 'SUCCESS' and job_id:
                # Fetch the result
                return self.get_result(str(job_id))
            else:
                logger.warning(f"LlamaParse job {job_id} failed with status: {status}")
                return {}
                
        except Exception as e:
            logger.error(f"Error handling LlamaParse webhook: {str(e)}")
            return {}

    @log_extractor_method()
    def calculate_cost(self, page_count: int, api_response: Optional[dict] = None) -> float:
        """
        Calculate cost for LlamaParse extraction.
        Pricing: $0.003 per page
        """

        cost_calculator = CostCalculator()
        return cost_calculator.calculate_cost("LlamaParse", page_count=page_count)

    @log_extractor_method()
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Get usage metrics for LlamaParse extraction.
        """
        page_count = 0
        if self._last_result:
            page_count = len(self._last_result)
        
        return {
            "extractor": "LlamaParse",
            "page_count": page_count,
            "estimated_cost": self.calculate_cost(page_count)
        }
