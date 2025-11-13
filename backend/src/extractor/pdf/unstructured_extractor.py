# from unstructured.partition.pdf import partition_pdf
# from typing import Dict, Any, Union
# from src.interface import PDFExtractorInterface
from loguru import logger




# class UnstructuredExtractor(PDFExtractorInterface):
#     def __init__(self):
#         self._last_result = None

#     def get_information(self) -> dict:
#         return {
#             "name": "Unstructured",
#             "type": "sync",
#             "supports": ["text", "tables"],
#             "description": "Extracts text, tables, and document structure from PDFs using Unstructured.io library."
#         }

#     def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
#         """
#         Extract content from PDF using Unstructured synchronously.
#         Returns a per-page mapping with extracted text and tables.
#         """
#         page_contents: Dict[int, Dict[str, Any]] = {}

#         try:
#             # Partition the PDF with various strategies
#             # strategy options: "auto", "hi_res", "fast", "ocr_only"
#             strategy = kwargs.get("strategy", "auto")
            
#             elements = partition_pdf(
#                 filename=file_path,
#                 strategy="fast",  # Changed from "auto"
#                 infer_table_structure=False,  # Disable if causing issues
#                 extract_images_in_pdf=False,
#                 include_page_breaks=True,
#                 max_partition=1500  # Add memory limit
#             )

#             # Group elements by page number
#             page_elements: Dict[int, list] = {}
#             current_page = 1
            
#             for element in elements:
#                 page_num = getattr(element.metadata, 'page_number', current_page)
                
#                 # Ensure page_num is not None and is a valid integer
#                 if page_num is None or not isinstance(page_num, int):
#                     page_num = current_page
                
#                 if page_num not in page_elements:
#                     page_elements[page_num] = {
#                         'text': [],
#                         'tables': [],
#                         'titles': [],
#                         'other': []
#                     }
                
#                 # Categorize element by type
#                 element_type = type(element).__name__
#                 element_text = str(element)
                
#                 if element_type == 'Table':
#                     page_elements[page_num]['tables'].append(element_text)
#                 elif element_type == 'Title':
#                     page_elements[page_num]['titles'].append(element_text)
#                 elif element_type in ['NarrativeText', 'Text', 'ListItem']:
#                     page_elements[page_num]['text'].append(element_text)
#                 else:
#                     page_elements[page_num]['other'].append(element_text)

#             # Build structured result per page
#             # Filter out any None values and ensure we have valid page numbers
#             valid_pages = [p for p in page_elements.keys() if p is not None and isinstance(p, int)]
#             max_page = max(valid_pages) if valid_pages else 1
            
#             for page_num in range(1, max_page + 1):
#                 if page_num in page_elements:
#                     page_data = page_elements[page_num]
                    
#                     # Combine all text elements
#                     all_text = '\n\n'.join(
#                         page_data['titles'] + 
#                         page_data['text'] + 
#                         page_data['other']
#                     )
                    
#                     tables_text = '\n\n'.join(page_data['tables'])
                    
#                     page_contents[page_num] = {
#                         "content": {
#                             "TEXT": all_text,
#                             "TABLES": tables_text,
#                             "TITLES": '\n'.join(page_data['titles'])
#                         },
#                         "metadata": {
#                             "extractor": "Unstructured",
#                             "page_number": page_num,
#                             "tables_found": len(page_data['tables']),
#                             "titles_found": len(page_data['titles']),
#                             "strategy": strategy
#                         }
#                     }
#                 else:
#                     # Empty page
#                     page_contents[page_num] = {
#                         "content": {
#                             "TEXT": "",
#                             "TABLES": "",
#                             "TITLES": ""
#                         },
#                         "metadata": {
#                             "extractor": "Unstructured",
#                             "page_number": page_num,
#                             "tables_found": 0,
#                             "titles_found": 0,
#                             "strategy": strategy
#                         }
#                     }

#         except Exception as e:
#             logger.warning(f"Unstructured extraction failed: {str(e)}")
#             page_contents = {
#                 1: {
#                     "content": {
#                         "TEXT": "", 
#                         "TABLES": "", 
#                         "TITLES": ""
#                     }, 
#                     "metadata": {
#                         "extractor": "Unstructured",
#                         "page_number": 1,
#                         "error": str(e),
#                         "tables_found": 0,
#                         "titles_found": 0
#                     }
#                 }
#             }

#         self._last_result = page_contents
#         return True

#     def get_status(self, job_id: str) -> str:
#         """
#         Unstructured is synchronous; extraction always completes immediately.
#         """
#         return "succeeded"

#     def get_result(self, job_id: str) -> Union[str, dict]:
#         """
#         job_id is unused for sync extractors; returns last result.
#         """
#         return self._last_result

#     def supports_webhook(self) -> bool:
#         """
#         Unstructured does not support webhooks.
#         """
#         return False

#     def handle_webhook(self, payload: dict) -> Union[str, dict]:
#         """
#         Webhook handling not supported for Unstructured.
#         """
#         raise NotImplementedError("Unstructured does not support webhooks")
