from enum import Enum

class ExtractionStatus(str, Enum):
    NOT_STARTED = "Not Started"
    PROCESSING = "Processing"
    SUCCESS = "Success"
    FAILURE = "Failure"

class PDFExtractorType(str, Enum):
    PYPDF2 = "PyPDF2"
    PYMUPDF = "PyMuPDF"
    PDFPLUMBER = "PDFPlumber"
    CAMELOT = "Camelot"
    TESSERACT = "Tesseract"
    TEXTRACT = "Textract"
    MATHPIX = "Mathpix"
    TABULA = "Tabula"
    UNSTRUCTURED = "Unstructured"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT5 = "gpt-5"
    OPENAI_GPT5_MINI = "gpt-5-mini"
    MARKITDOWN = "MarkItDown"
    LLAMAPARSE = "LlamaParse"
    AZURE_DI = "AzureDI"

class ImageExtractorType(str, Enum):
    TESSERACT = "Tesseract"
    TEXTRACT = "Textract"
    MATHPIX = "Mathpix"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT5 = "gpt-5"
    OPENAI_GPT5_MINI = "gpt-5-mini"
    AZURE_DI = "AzureDI"

class FeedbackType(str, Enum):
    SINGLE = "Single"
    COMPARISON = "Comparison"

class AudioExtractorType(str, Enum):
    WHISPER_OPENAI = "whisper-openai"
    ASSEMBLYAI = "assemblyai"
    AWS_TRANSCRIBE = "aws-transcribe"
