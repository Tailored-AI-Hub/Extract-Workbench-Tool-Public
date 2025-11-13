from src.models.enums import ImageExtractorType
from src.extractor.image.tesseract_extractor import TesseractImageExtractor
from src.extractor.image.textract_extractor import TextractImageExtractor
from src.extractor.image.mathpix_extractor import MathpixImageExtractor
from src.extractor.image.openai_vision_extractor import OpenAIVisionImageExtractor
from src.extractor.image.azure_extractor import AzureDIImageExtractor

# Map enum values → extractor classes
IMAGE_READER_MAP = {
    ImageExtractorType.TESSERACT.value: TesseractImageExtractor,
    ImageExtractorType.TEXTRACT.value: TextractImageExtractor,
    ImageExtractorType.MATHPIX.value: MathpixImageExtractor,
    ImageExtractorType.OPENAI_GPT4O_MINI.value: lambda: OpenAIVisionImageExtractor("gpt-4o-mini"),
    ImageExtractorType.OPENAI_GPT4O.value: lambda: OpenAIVisionImageExtractor("gpt-4o"),
    ImageExtractorType.OPENAI_GPT5.value: lambda: OpenAIVisionImageExtractor("gpt-5"),
    ImageExtractorType.OPENAI_GPT5_MINI.value: lambda: OpenAIVisionImageExtractor("gpt-5-mini"),
    ImageExtractorType.AZURE_DI.value: AzureDIImageExtractor,
}


def get_image_reader(extractor_type: str):
    """
    Factory method to return an initialized image extractor
    based on extractor_type (string/enum value).
    """
    if extractor_type not in IMAGE_READER_MAP:
        raise ValueError(f"Unknown image extractor type: {extractor_type}")
    return IMAGE_READER_MAP[extractor_type]()

