from src.models.enums import AudioExtractorType
from src.extractor.audio.whisper_openai_extractor import WhisperOpenAIExtractor

# Map enum values → extractor classes
# Lazy import for AssemblyAI to avoid import errors if not installed
AUDIO_READER_MAP = {
    AudioExtractorType.WHISPER_OPENAI.value: WhisperOpenAIExtractor,
}


def get_audio_reader(extractor_type: str):
    if extractor_type not in AUDIO_READER_MAP:
        # Lazy load AssemblyAI extractor
        if extractor_type == AudioExtractorType.ASSEMBLYAI.value:
            from src.extractor.audio.assemblyai_extractor import AssemblyAIExtractor
            AUDIO_READER_MAP[AudioExtractorType.ASSEMBLYAI.value] = AssemblyAIExtractor
        # Lazy load AWS Transcribe extractor
        elif extractor_type == AudioExtractorType.AWS_TRANSCRIBE.value:
            from src.extractor.audio.aws_transcribe_extractor import AWSTranscribeExtractor
            AUDIO_READER_MAP[AudioExtractorType.AWS_TRANSCRIBE.value] = AWSTranscribeExtractor
        else:
            raise ValueError(f"Unknown audio extractor type: {extractor_type}")
    klass = AUDIO_READER_MAP[extractor_type]
    return klass()


