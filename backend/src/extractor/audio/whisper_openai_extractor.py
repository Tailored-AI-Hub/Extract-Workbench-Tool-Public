from typing import Dict, Any
from openai import OpenAI
from pathlib import Path
import os
from .interface import AudioExtractorInterface
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method


class WhisperOpenAIExtractor(AudioExtractorInterface):
    """
    Audio extractor using OpenAI's Whisper API for transcription.
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = OpenAI(api_key=api_key)
        self.cost_calculator = CostCalculator()
    
    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "Whisper (OpenAI)",
            "type": "sync",
            "supports": ["transcript", "timestamps"],
            "description": "Transcribe audio using OpenAI's Whisper API",
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Transcribe audio file using OpenAI Whisper API.
        Returns segments with transcribed text and timestamps.
        Includes empty timestamps for gaps in transcription.
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Open and transcribe the audio file with verbose_json to get segments
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            segments = {}
            segment_num = 1
            
            # Check if we have segments with timestamps
            # The verbose_json format includes a 'segments' field
            transcript_segments = None
            if hasattr(transcript, 'segments'):
                transcript_segments = transcript.segments
            elif isinstance(transcript, dict) and 'segments' in transcript:
                transcript_segments = transcript['segments']
            
            if transcript_segments:
                last_end_time = 0.0
                
                for segment in transcript_segments:
                    # Handle both object attributes and dict access
                    if hasattr(segment, 'start'):
                        start_time = getattr(segment, 'start', 0.0)
                        end_time = getattr(segment, 'end', 0.0)
                        text = getattr(segment, 'text', '').strip()
                    elif isinstance(segment, dict):
                        start_time = segment.get('start', 0.0)
                        end_time = segment.get('end', 0.0)
                        text = segment.get('text', '').strip()
                    else:
                        continue
                    
                    # Add empty timestamp segment if there's a gap before this segment
                    if start_time > last_end_time + 0.1:  # 0.1 second threshold for gaps
                        gap_start_ms = int(last_end_time * 1000)
                        gap_end_ms = int(start_time * 1000)
                        segments[segment_num] = {
                            "text": "",
                            "start": gap_start_ms,
                            "end": gap_end_ms,
                            "is_empty": True,
                        }
                        segment_num += 1
                    
                    # Add the actual segment with text
                    start_ms = int(start_time * 1000) if start_time is not None else None
                    end_ms = int(end_time * 1000) if end_time is not None else None
                    
                    segments[segment_num] = {
                        "text": text,
                        "start": start_ms,
                        "end": end_ms,
                        "language": getattr(transcript, 'language', 'unknown') if hasattr(transcript, 'language') else 'unknown',
                    }
                    segment_num += 1
                    last_end_time = end_time
            else:
                # Fallback: if no segments, return full transcript as single segment
                text = transcript.text if hasattr(transcript, 'text') else str(transcript)
                segments[1] = {
                    "text": text,
                    "start": None,
                    "end": None,
                    "language": getattr(transcript, 'language', 'unknown') if hasattr(transcript, 'language') else 'unknown',
                }
            
            return segments
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            # Return error message in transcript
            error_msg = f"Error transcribing audio: {str(e)}"
            return {
                1: {
                    "text": error_msg,
                    "start": None,
                    "end": None,
                    "error": str(e),
                }
            }

    @log_extractor_method()
    def calculate_cost(self, duration_seconds: float, **kwargs) -> float:
        """
        Calculate cost for OpenAI Whisper based on duration.
        """
        return self.cost_calculator.calculate_audio_cost(
            service_name="openai-whisper",
            duration_seconds=duration_seconds,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for OpenAI Whisper.
        """
        try:
            import mutagen
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration_seconds = audio_file.info.length
                return {
                    "duration_seconds": duration_seconds,
                    "service": "openai-whisper",
                    "estimated_cost": self.calculate_cost(duration_seconds, **kwargs)
                }
        except ImportError:
            # Fallback if mutagen not available
            pass
        except Exception as e:
            print(f"Error getting audio duration: {e}")
        
        return {
            "duration_seconds": 0.0,
            "service": "openai-whisper",
            "estimated_cost": 0.0
        }

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return False

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Dict[str, Any]:
        return {}

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Dict[str, Any]:
        """
        Webhook handling not supported for Whisper OpenAI.
        """
        raise NotImplementedError("Whisper OpenAI does not support webhooks")

