from src.extractor.pdf.pdfplumber_extractor import PDFPlumberExtractor
from src.extractor.pdf.pymupdf_extractor import PyMuPDFExtractor
# from src.extractor.pdf.camelot_extractor import CamelotExtractor
from src.extractor.pdf.pypdf2_extractor import PyPDF2Extractor
from src.extractor.pdf.tesseract_extractor import TesseractExtractor
from src.extractor.pdf.textract_extractor import TextractExtractor
from src.extractor.pdf.markitdown_extractor import MarkItDownExtractor
from src.extractor.pdf.llamaparse import LlamaParseExtractor
from src.extractor.pdf.mathpix_extractor import MathpixExtractor
from src.extractor.pdf.openai_vision_extractor import OpenAIVisionExtractor
from src.extractor.pdf.azure_extractor import AzureDIExtractor
# from src.extractor.pdf.tabula_extractor import TabulaExtractor
# from src.extractor.pdf.unstructured_extractor import UnstructuredExtractor
from src.models import PDFExtractorType

# Map enum values → reader classes
READER_MAP = {
    PDFExtractorType.PYMUPDF.value: PyMuPDFExtractor,
    PDFExtractorType.PDFPLUMBER.value: PDFPlumberExtractor,
    # PDFExtractorType.CAMELOT.value: CamelotExtractor,
    PDFExtractorType.PYPDF2.value: PyPDF2Extractor,
    PDFExtractorType.TESSERACT.value: TesseractExtractor,
    PDFExtractorType.TEXTRACT.value: TextractExtractor,
    PDFExtractorType.MARKITDOWN.value: MarkItDownExtractor,
    PDFExtractorType.LLAMAPARSE.value: LlamaParseExtractor,
    PDFExtractorType.MATHPIX.value: MathpixExtractor,
    PDFExtractorType.OPENAI_GPT4O_MINI.value: lambda: OpenAIVisionExtractor("gpt-4o-mini"),
    PDFExtractorType.OPENAI_GPT4O.value: lambda: OpenAIVisionExtractor("gpt-4o"),
    PDFExtractorType.OPENAI_GPT5.value: lambda: OpenAIVisionExtractor("gpt-5"),
    PDFExtractorType.OPENAI_GPT5_MINI.value: lambda: OpenAIVisionExtractor("gpt-5-mini"),
    PDFExtractorType.AZURE_DI.value: AzureDIExtractor,
    # PDFExtractorType.TABULA.value: TabulaExtractor,
    # PDFExtractorType.UNSTRUCTURED.value: UnstructuredExtractor,
}


def get_reader(extractor_type: str):
    """
    Factory method to return an initialized reader
    based on extractor_type (string/enum value).
    """
    if extractor_type not in READER_MAP:
        raise ValueError(f"Unknown extractor type: {extractor_type}")
    return READER_MAP[extractor_type]()


