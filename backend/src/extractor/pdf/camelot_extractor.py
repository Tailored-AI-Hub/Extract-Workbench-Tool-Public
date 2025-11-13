# import camelot as camelot_py
# from typing import Dict, Any, Union
# from src.interface import PDFExtractorInterface
# from loguru import logger


# class CamelotExtractor(PDFExtractorInterface):
#     def __init__(self):
#         self._last_result = None

#     def get_information(self) -> dict:
#         return {
#             "name": "Camelot",
#             "type": "sync",
#             "supports": ["tables"],
#             "description": "Extracts structured tables from PDFs using Camelot."
#         }

#     def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
#         """
#         Extract tables from PDF using Camelot synchronously.
#         Returns a per-page mapping with extracted table text.
#         """
#         page_contents: Dict[int, Dict[str, Any]] = {}
#         try:
#             tables = camelot_py.read_pdf(file_path, pages="all")
#             # Group tables by page number
#             page_tables: Dict[int, list] = {}
#             for table in tables:
#                 page_num = table.page
#                 if page_num not in page_tables:
#                     page_tables[page_num] = []
#                 page_tables[page_num].append(table.df.to_string())
#             # Build structured result per page
#             for page_num in range(1, (max(page_tables.keys()) + 1) if page_tables else 1):
#                 joined_tables = "\n\n".join(page_tables.get(page_num, []))
#                 page_contents[page_num] = {
#                     "content": {
#                         "TABLES": joined_tables
#                     },
#                     "metadata": {
#                         "extractor": "Camelot",
#                         "tables_found": len(page_tables.get(page_num, [])),
#                         "total_tables": len(tables)
#                     }
#                 }

#         except Exception as e:
#             logger.warning(f"Camelot extraction failed: {str(e)}")
#             page_contents = {1: {"content": {"TABLES": ""}, "metadata": {"error": str(e)}}}

#         self._last_result = page_contents
#         return True

#     def get_status(self, job_id: str) -> str:
#         """
#         Camelot is synchronous; extraction always completes immediately.
#         """
#         return "succeeded"

#     def get_result(self, job_id: str) -> Union[str, dict]:
#         """
#         job_id is unused for sync extractors; returns last result.
#         """
#         return self._last_result

#     def supports_webhook(self) -> bool:
#         """
#         Camelot does not support webhooks.
#         """
#         return False

#     def handle_webhook(self, payload: dict) -> Union[str, dict]:
#         """
#         Webhook handling not supported for Camelot.
#         """
#         raise NotImplementedError("Camelot does not support webhooks")
