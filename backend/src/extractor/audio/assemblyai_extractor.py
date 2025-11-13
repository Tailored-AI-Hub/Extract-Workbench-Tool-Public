from typing import Dict, Any, Union
import os
import json
from .interface import AudioExtractorInterface
from .utils import round_confidence
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method

try:
    import assemblyai as aai
except ImportError:
    aai = None


class AssemblyAIExtractor(AudioExtractorInterface):
    """
    Audio extractor using Assembly AI for transcription.
    """
    
    def _transcript_to_dict(self, transcript) -> Dict[str, Any]:
        """
        Convert AssemblyAI transcript object to a dictionary.
        Extracts all available fields including text, words, entities, etc.
        """
        result = {}
        
        # Extract basic fields
        if hasattr(transcript, 'text'):
            result['text'] = transcript.text
        elif hasattr(transcript, 'get'):
            result['text'] = transcript.get('text', '')
        
        # Extract words
        if hasattr(transcript, 'words') and transcript.words:
            words = []
            for word in transcript.words:
                if hasattr(word, '__dict__'):
                    word_dict = {}
                    for attr in ['text', 'start', 'end', 'confidence']:
                        if hasattr(word, attr):
                            val = getattr(word, attr)
                            # Convert to seconds (AssemblyAI returns timestamps in milliseconds)
                            if attr in ['start', 'end'] and val is not None:
                                # Convert milliseconds to seconds, round to 3 decimal places
                                word_dict[attr] = round(val / 1000.0, 3)
                            elif attr == 'confidence':
                                word_dict[attr] = round_confidence(val)
                            else:
                                word_dict[attr] = val
                    words.append(word_dict)
                elif isinstance(word, dict):
                    word_dict = word.copy()
                    # Convert timestamps from milliseconds to seconds
                    for attr in ['start', 'end']:
                        if attr in word_dict and word_dict[attr] is not None:
                            # Convert milliseconds to seconds, round to 3 decimal places
                            word_dict[attr] = round(word_dict[attr] / 1000.0, 3)
                    # Round confidence if present
                    if 'confidence' in word_dict:
                        word_dict['confidence'] = round_confidence(word_dict['confidence'])
                    words.append(word_dict)
            if words:
                result['items'] = words
        
        # Extract entities
        if hasattr(transcript, 'entities') and transcript.entities:
            entities = []
            for entity in transcript.entities:
                if hasattr(entity, '__dict__'):
                    entity_dict = {}
                    for attr in ['entity_type', 'text', 'start', 'end']:
                        if hasattr(entity, attr):
                            val = getattr(entity, attr)
                            if attr in ['start', 'end'] and val is not None:
                                if val < 100:
                                    entity_dict[attr] = int(val * 1000)
                                else:
                                    entity_dict[attr] = int(val)
                            else:
                                entity_dict[attr] = val
                    entities.append(entity_dict)
                elif isinstance(entity, dict):
                    entity_dict = entity.copy()
                    for attr in ['start', 'end']:
                        if attr in entity_dict and entity_dict[attr] is not None:
                            if entity_dict[attr] < 100:
                                entity_dict[attr] = int(entity_dict[attr] * 1000)
                            else:
                                entity_dict[attr] = int(entity_dict[attr])
                    entities.append(entity_dict)
            if entities:
                result['entities'] = entities
        
        # Extract content safety labels
        if hasattr(transcript, 'content_safety_labels'):
            safety_labels = transcript.content_safety_labels
            if safety_labels:
                if hasattr(safety_labels, '__dict__'):
                    result['content_safety_labels'] = {
                        'status': getattr(safety_labels, 'status', None),
                        'results': getattr(safety_labels, 'results', []),
                        'summary': getattr(safety_labels, 'summary', {}),
                    }
                elif isinstance(safety_labels, dict):
                    result['content_safety_labels'] = safety_labels
        
        # Extract auto highlights
        if hasattr(transcript, 'auto_highlights'):
            highlights = transcript.auto_highlights
            if highlights:
                if hasattr(highlights, '__dict__'):
                    result['auto_highlights'] = {
                        'status': getattr(highlights, 'status', None),
                        'results': getattr(highlights, 'results', []),
                    }
                elif isinstance(highlights, dict):
                    result['auto_highlights'] = highlights
        
        # Extract utterances if available
        if hasattr(transcript, 'utterances') and transcript.utterances:
            utterances = []
            for utterance in transcript.utterances:
                if hasattr(utterance, '__dict__'):
                    utt_dict = {}
                    for attr in ['text', 'start', 'end', 'confidence', 'speaker']:
                        if hasattr(utterance, attr):
                            val = getattr(utterance, attr)
                            if attr in ['start', 'end'] and val is not None:
                                if val < 100:
                                    utt_dict[attr] = int(val * 1000)
                                else:
                                    utt_dict[attr] = int(val)
                            elif attr == 'confidence':
                                utt_dict[attr] = round_confidence(val)
                            else:
                                utt_dict[attr] = val
                    utterances.append(utt_dict)
                elif isinstance(utterance, dict):
                    utt_dict = utterance.copy()
                    for attr in ['start', 'end']:
                        if attr in utt_dict and utt_dict[attr] is not None:
                            if utt_dict[attr] < 100:
                                utt_dict[attr] = int(utt_dict[attr] * 1000)
                            else:
                                utt_dict[attr] = int(utt_dict[attr])
                    utterances.append(utt_dict)
            if utterances:
                result['utterances'] = utterances
        
        # Extract segments if available
        if hasattr(transcript, 'segments') and transcript.segments:
            segments = []
            for seg in transcript.segments:
                if hasattr(seg, '__dict__'):
                    seg_dict = {}
                    for attr in ['text', 'start', 'end', 'confidence']:
                        if hasattr(seg, attr):
                            val = getattr(seg, attr)
                            if attr in ['start', 'end'] and val is not None:
                                if val < 100:
                                    seg_dict[attr] = int(val * 1000)
                                else:
                                    seg_dict[attr] = int(val)
                            elif attr == 'confidence':
                                seg_dict[attr] = round_confidence(val)
                            else:
                                seg_dict[attr] = val
                    segments.append(seg_dict)
                elif isinstance(seg, dict):
                    seg_dict = seg.copy()
                    for attr in ['start', 'end']:
                        if attr in seg_dict and seg_dict[attr] is not None:
                            if seg_dict[attr] < 100:
                                seg_dict[attr] = int(seg_dict[attr] * 1000)
                            else:
                                seg_dict[attr] = int(seg_dict[attr])
                    segments.append(seg_dict)
            if segments:
                result['segments'] = segments
        
        # Extract other common fields
        for attr in ['id', 'status', 'language_code', 'acoustic_model', 'language_model', 'punctuation_model']:
            if hasattr(transcript, attr):
                val = getattr(transcript, attr)
                if val is not None:
                    result[attr] = val
        
        return result
    
    def __init__(self):
        if aai is None:
            raise ImportError(
                "assemblyai package is not installed. "
                "Please install it with: pip install assemblyai>=0.28.0"
            )
        api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not api_key:
            raise ValueError("ASSEMBLYAI_API_KEY environment variable is not set")
        aai.settings.api_key = api_key
        self.transcriber = aai.Transcriber()
        self.cost_calculator = CostCalculator()
    
    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "AssemblyAI",
            "type": "async",
            "supports": ["transcript", "timestamps"],
            "description": "Transcribe audio using AssemblyAI's transcription API",
        }

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Transcribe audio file using Assembly AI.
        Returns segments with transcribed text.
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Configure transcription
            # Note: word_timestamps is enabled by default in newer SDK versions
            # Use minimal config - utterances are available by default
            config = aai.TranscriptionConfig()
            
            # Transcribe the audio file
            transcript = self.transcriber.transcribe(file_path, config)
            
            # Wait for transcription to complete
            transcript.wait_for_completion()
            
            # Check if transcription was successful
            if transcript.status == aai.TranscriptStatus.error:
                error_msg = f"Assembly AI transcription error: {transcript.error}"
                raise RuntimeError(error_msg)
            
            # Convert transcript to dictionary for raw JSON storage
            raw_transcript_json = self._transcript_to_dict(transcript)
            
            # Extract segments
            segments = {}
            first_segment_key = None
            
            # Try to use utterances first (sentence-level segments)
            if hasattr(transcript, 'utterances') and transcript.utterances:
                # Use utterances (sentence-level segments) if available
                for idx, utterance in enumerate(transcript.utterances, start=1):
                    if first_segment_key is None:
                        first_segment_key = idx
                    segments[idx] = {
                        "content": {
                            "TEXT": utterance.text,
                            "COMBINED": utterance.text,
                        },
                        "metadata": {
                            "extractor": "assemblyai",
                            "segment": idx,
                            "start_ms": int(utterance.start) if utterance.start is not None else None,
                            "end_ms": int(utterance.end) if utterance.end is not None else None,
                            "confidence": round_confidence(utterance.confidence if hasattr(utterance, 'confidence') else None),
                        },
                    }
            # Try chapters/segments if available (requires auto_chapters=True)
            elif hasattr(transcript, 'segments') and transcript.segments:
                # Use timestamped segments if available
                for idx, segment in enumerate(transcript.segments, start=1):
                    if first_segment_key is None:
                        first_segment_key = idx
                    segments[idx] = {
                        "content": {
                            "TEXT": segment.text,
                            "COMBINED": segment.text,
                        },
                        "metadata": {
                            "extractor": "assemblyai",
                            "segment": idx,
                            "start_ms": int(segment.start) if segment.start is not None else None,
                            "end_ms": int(segment.end) if segment.end is not None else None,
                            "confidence": round_confidence(segment.confidence if hasattr(segment, 'confidence') else None),
                        },
                    }
            # Fallback: try to use words to create segments with timestamps
            elif hasattr(transcript, 'words') and transcript.words:
                # Create segments from words if utterances/segments not available
                # Group words into segments based on natural pauses (similar to AWS Transcribe logic)
                words = transcript.words
                current_segment_data = []  # Store tuples of (word_text, start_ms, end_ms)
                segment_num = 1
                last_end_time = 0.0
                pause_threshold = 2000.0  # 2 seconds pause = new segment (in milliseconds)
                
                for word in words:
                    # Handle both object attributes and dict access
                    if hasattr(word, 'start'):
                        word_start = getattr(word, 'start', None)
                        word_end = getattr(word, 'end', None)
                        word_text = getattr(word, 'text', '')
                    elif isinstance(word, dict):
                        word_start = word.get('start')
                        word_end = word.get('end')
                        word_text = word.get('text', '')
                    else:
                        continue
                    
                    # Convert to milliseconds - AssemblyAI returns timestamps in milliseconds
                    # Check if already in milliseconds (values > 1000 are likely milliseconds)
                    # or in seconds (values < 100 are likely seconds)
                    if word_start is not None:
                        # If value is less than 100, assume seconds (convert to ms)
                        # Otherwise assume already in milliseconds
                        if word_start < 100:
                            word_start_ms = int(word_start * 1000)
                        else:
                            word_start_ms = int(word_start)
                        
                        if word_end is not None:
                            if word_end < 100:
                                word_end_ms = int(word_end * 1000)
                            else:
                                word_end_ms = int(word_end)
                        else:
                            word_end_ms = None
                    else:
                        continue
                    
                    # Check if we should start a new segment (gap > threshold)
                    if word_start_ms - last_end_time > pause_threshold and current_segment_data:
                        # Save current segment
                        segment_text = ' '.join([w[0] for w in current_segment_data])
                        if segment_text.strip():
                            # Get timestamps from first and last words in segment
                            first_start_ms = current_segment_data[0][1]
                            last_end_ms = current_segment_data[-1][2] if current_segment_data[-1][2] is not None else current_segment_data[-1][1]
                            
                            if first_segment_key is None:
                                first_segment_key = segment_num
                            segments[segment_num] = {
                                "content": {
                                    "TEXT": segment_text,
                                    "COMBINED": segment_text,
                                },
                                "metadata": {
                                    "extractor": "assemblyai",
                                    "segment": segment_num,
                                    "start_ms": first_start_ms,
                                    "end_ms": last_end_ms,
                                },
                            }
                            segment_num += 1
                        current_segment_data = []
                    
                    # Store word data with converted timestamps
                    current_segment_data.append((word_text, word_start_ms, word_end_ms))
                    last_end_time = word_end_ms if word_end_ms is not None else word_start_ms
                
                # Add final segment
                if current_segment_data:
                    segment_text = ' '.join([w[0] for w in current_segment_data])
                    if segment_text.strip():
                        # Get timestamps from first and last words in segment
                        first_start_ms = current_segment_data[0][1]
                        last_end_ms = current_segment_data[-1][2] if current_segment_data[-1][2] is not None else current_segment_data[-1][1]
                        
                        if first_segment_key is None:
                            first_segment_key = segment_num
                        segments[segment_num] = {
                            "content": {
                                "TEXT": segment_text,
                                "COMBINED": segment_text,
                            },
                            "metadata": {
                                "extractor": "assemblyai",
                                "segment": segment_num,
                                "start_ms": first_start_ms,
                                "end_ms": last_end_ms,
                            },
                        }
                
                # Store raw transcript JSON before returning (if segments were created)
                if segments and first_segment_key is not None and first_segment_key in segments:
                    segments[first_segment_key]["metadata"]["raw_transcript_json"] = raw_transcript_json
                
                # Only return if we created segments
                if segments:
                    return segments
            else:
                # Final fallback: return full transcript as single segment
                text = transcript.text if transcript.text else ""
                first_segment_key = 1
                segments[1] = {
                    "content": {
                        "TEXT": text,
                        "COMBINED": text,
                    },
                    "metadata": {
                        "extractor": "assemblyai",
                        "segment": 1,
                    },
                }
            
            # Store raw transcript JSON in the first segment's metadata
            if first_segment_key is not None and first_segment_key in segments:
                segments[first_segment_key]["metadata"]["raw_transcript_json"] = raw_transcript_json
            
            return segments
        except Exception as e:
            print(f"Error transcribing audio with Assembly AI: {e}")
            error_msg = f"Error transcribing audio: {str(e)}"
            return {
                1: {
                    "content": {
                        "TEXT": error_msg,
                        "COMBINED": error_msg,
                    },
                    "metadata": {
                        "extractor": "assemblyai",
                        "segment": 1,
                        "error": str(e),
                    },
                }
            }

    @log_extractor_method()
    def calculate_cost(self, duration_seconds: float, **kwargs) -> float:
        """
        Calculate cost for AssemblyAI transcription based on duration.
        """
        return self.cost_calculator.calculate_audio_cost(
            service_name="assemblyai",
            duration_seconds=duration_seconds,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for AssemblyAI transcription.
        """
        try:
            import mutagen
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration_seconds = audio_file.info.length
                return {
                    "duration_seconds": duration_seconds,
                    "service": "assemblyai",
                    "estimated_cost": self.calculate_cost(duration_seconds, **kwargs)
                }
        except ImportError:
            # Fallback if mutagen not available
            pass
        except Exception as e:
            print(f"Error getting audio duration: {e}")
        
        return {
            "duration_seconds": 0.0,
            "service": "assemblyai", 
            "estimated_cost": 0.0
        }

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return True

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Check the status of a transcription job.
        Note: This requires storing transcript objects or querying by job_id.
        For now, returns a placeholder.
        """
        # TODO: Implement job tracking if needed
        return "succeeded"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, Dict[str, Any]]:
        """
        Fetch the final parsed output for a job.
        Note: This requires storing transcript objects or querying by job_id.
        """
        # TODO: Implement job tracking if needed
        return {}

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, Dict[str, Any]]:
        """
        Handle Assembly AI webhook payloads.
        Assembly AI webhooks include transcript data when status is 'completed'.
        """
        try:
            status = payload.get("status")
            if status == "completed":
                transcript_data = payload.get("transcript", {})
                # Store raw transcript JSON from webhook
                raw_transcript_json = transcript_data.copy()
                segments = {}
                first_segment_key = None
                
                # Try to use utterances first (sentence-level segments) - same priority as read() method
                transcript_utterances = transcript_data.get("utterances", [])
                if transcript_utterances:
                    # Use utterances (sentence-level segments) if available
                    for idx, utterance in enumerate(transcript_utterances, start=1):
                        if first_segment_key is None:
                            first_segment_key = idx
                        # Handle both dict and object access
                        if isinstance(utterance, dict):
                            start_val = utterance.get("start")
                            end_val = utterance.get("end")
                            text = utterance.get("text", "")
                            confidence = utterance.get("confidence")
                        else:
                            start_val = getattr(utterance, 'start', None)
                            end_val = getattr(utterance, 'end', None)
                            text = getattr(utterance, 'text', '')
                            confidence = getattr(utterance, 'confidence', None) if hasattr(utterance, 'confidence') else None
                        
                        # Convert to int milliseconds (AssemblyAI returns timestamps in milliseconds)
                        start_ms = int(start_val) if start_val is not None else None
                        end_ms = int(end_val) if end_val is not None else None
                        
                        segments[idx] = {
                            "content": {
                                "TEXT": text,
                                "COMBINED": text,
                            },
                            "metadata": {
                                "extractor": "assemblyai",
                                "segment": idx,
                                "start_ms": start_ms,
                                "end_ms": end_ms,
                                "confidence": round_confidence(confidence),
                            },
                        }
                # Try chapters/segments if available (requires auto_chapters=True)
                elif transcript_data.get("segments", []):
                    transcript_segments = transcript_data.get("segments", [])
                    # Use timestamped segments if available
                    for idx, segment in enumerate(transcript_segments, start=1):
                        if first_segment_key is None:
                            first_segment_key = idx
                        # Handle both dict and object access
                        if isinstance(segment, dict):
                            start_val = segment.get("start")
                            end_val = segment.get("end")
                            text = segment.get("text", "")
                            confidence = segment.get("confidence")
                        else:
                            start_val = getattr(segment, 'start', None)
                            end_val = getattr(segment, 'end', None)
                            text = getattr(segment, 'text', '')
                            confidence = getattr(segment, 'confidence', None) if hasattr(segment, 'confidence') else None
                        
                        # Convert to int milliseconds (AssemblyAI returns timestamps in milliseconds)
                        start_ms = int(start_val) if start_val is not None else None
                        end_ms = int(end_val) if end_val is not None else None
                        
                        segments[idx] = {
                            "content": {
                                "TEXT": text,
                                "COMBINED": text,
                            },
                            "metadata": {
                                "extractor": "assemblyai",
                                "segment": idx,
                                "start_ms": start_ms,
                                "end_ms": end_ms,
                                "confidence": round_confidence(confidence),
                            },
                        }
                else:
                    # Fallback: use full text if no segments
                    text = transcript_data.get("text", "")
                    first_segment_key = 1
                    segments[1] = {
                        "content": {
                            "TEXT": text,
                            "COMBINED": text,
                        },
                        "metadata": {
                            "extractor": "assemblyai",
                            "segment": 1,
                        },
                    }
                
                # Store raw transcript JSON in the first segment's metadata
                if first_segment_key is not None and first_segment_key in segments:
                    segments[first_segment_key]["metadata"]["raw_transcript_json"] = raw_transcript_json
                
                return segments
            elif status == "error":
                error_msg = payload.get("error", "Unknown error")
                return {
                    1: {
                        "content": {
                            "TEXT": f"Assembly AI error: {error_msg}",
                            "COMBINED": f"Assembly AI error: {error_msg}",
                        },
                        "metadata": {
                            "extractor": "assemblyai",
                            "segment": 1,
                            "error": error_msg,
                        },
                    }
                }
            else:
                # Status is pending or processing
                return {}
        except Exception as e:
            print(f"Error handling Assembly AI webhook: {e}")
            return {
                1: {
                    "content": {
                        "TEXT": f"Error processing webhook: {str(e)}",
                        "COMBINED": f"Error processing webhook: {str(e)}",
                    },
                    "metadata": {
                        "extractor": "assemblyai",
                        "segment": 1,
                        "error": str(e),
                    },
                }
            }

