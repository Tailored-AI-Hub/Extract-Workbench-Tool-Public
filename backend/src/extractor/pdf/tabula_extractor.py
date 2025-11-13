# import tabula
# from typing import Dict, Any, Union
# from src.interface import PDFExtractorInterface
from loguru import logger




# class TabulaExtractor(PDFExtractorInterface):
#     def __init__(self):
#         self._last_result = None

#     def get_information(self) -> dict:
#         return {
#             "name": "Tabula",
#             "type": "sync",
#             "supports": ["tables"],
#             "description": "Extracts structured tables from PDFs using Tabula."
#         }

#     def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
#         """
#         Extract tables from PDF using Tabula synchronously.
#         Returns a per-page mapping with extracted table text.
#         """
#         page_contents: Dict[int, Dict[str, Any]] = {}

#         try:
#             # Get total number of pages
#             import PyPDF2
#             with open(file_path, 'rb') as f:
#                 pdf_reader = PyPDF2.PdfReader(f)
#                 total_pages = len(pdf_reader.pages)

#             # Extract tables page by page
#             total_tables = 0
            
#             for page_num in range(1, total_pages + 1):
#                 tables = tabula.read_pdf(
#                     file_path,
#                     pages=page_num,
#                     multiple_tables=True,
#                     pandas_options={'header': None}
#                 )
                
#                 # Process tables found on this page
#                 if tables and len(tables) > 0:
#                     page_table_strings = []
#                     for table in tables:
#                         if table is not None and not table.empty:
#                             page_table_strings.append(table.to_string())
                    
#                     joined_tables = "\n\n".join(page_table_strings)
#                     page_contents[page_num] = {
#                         "content": {
#                             "TABLES": joined_tables
#                         },
#                         "metadata": {
#                             "extractor": "Tabula",
#                             "tables_found": len(page_table_strings),
#                             "page_number": page_num
#                         }
#                     }
#                     total_tables += len(page_table_strings)
#                 else:
#                     # No tables on this page
#                     page_contents[page_num] = {
#                         "content": {
#                             "TABLES": ""
#                         },
#                         "metadata": {
#                             "extractor": "Tabula",
#                             "tables_found": 0,
#                             "page_number": page_num
#                         }
#                     }
            
#             # Add total tables count to all pages
#             for page_num in page_contents:
#                 page_contents[page_num]["metadata"]["total_tables"] = total_tables

#         except Exception as e:
#             logger.warning(f"Tabula extraction failed: {str(e)}")
#             page_contents = {1: {"content": {"TABLES": ""}, "metadata": {"error": str(e)}}}

#         self._last_result = page_contents
#         return True

#     def get_status(self, job_id: str) -> str:
#         """
#         Tabula is synchronous; extraction always completes immediately.
#         """
#         return "succeeded"

#     def get_result(self, job_id: str) -> Union[str, dict]:
#         """
#         job_id is unused for sync extractors; returns last result.
#         """
#         return self._last_result

#     def supports_webhook(self) -> bool:
#         """
#         Tabula does not support webhooks.
#         """
#         return False

#     def handle_webhook(self, payload: dict) -> Union[str, dict]:
#         """
#         Webhook handling not supported for Tabula.
#         """
#         raise NotImplementedError("Tabula does not support webhooks")