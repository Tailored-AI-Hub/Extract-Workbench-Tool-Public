from typing import Dict, Any, Union
import os
import boto3
import uuid
import time
import json
import urllib.request
from pathlib import Path
from botocore.exceptions import ClientError
from loguru import logger
from .interface import AudioExtractorInterface
from src.constants import AWS_BUCKET_NAME, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from src.cost_calculator import CostCalculator
from ..logger_decorator import log_extractor_method


class AWSTranscribeExtractor(AudioExtractorInterface):
    """
    Audio extractor using AWS Transcribe for transcription.
    """
    
    def __init__(self):
        # Validate AWS credentials
        if not AWS_BUCKET_NAME:
            raise ValueError("AWS_BUCKET_NAME environment variable is not set")
        if not AWS_REGION:
            raise ValueError("AWS_REGION environment variable is not set")
        
        # Initialize boto3 clients
        self.region = AWS_REGION
        self.bucket_name = AWS_BUCKET_NAME
        
        # Create Transcribe client with credentials if available
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            self.transcribe_client = boto3.client(
                'transcribe',
                region_name=self.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
            self.s3_client = boto3.client(
                's3',
                region_name=self.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )
        else:
            # Use default credentials (IAM role, environment, etc.)
            self.transcribe_client = boto3.client('transcribe', region_name=self.region)
            self.s3_client = boto3.client('s3', region_name=self.region)
        
        self.cost_calculator = CostCalculator()
    
    @log_extractor_method()
    def get_information(self) -> dict:
        return {
            "name": "AWS Transcribe",
            "type": "async",
            "supports": ["transcript", "timestamps"],
            "description": "Transcribe audio using AWS Transcribe service",
        }

    def _transform_transcript_data(self, transcript_data: dict) -> dict:
        """
        Transform AWS Transcribe transcript data to match desired format:
        - start_time -> start
        - end_time -> end  
        - content -> text in alternatives
        - Remove numbering from alternatives (no changes needed, just keep alternatives as-is)
        """
        if 'results' not in transcript_data:
            return transcript_data
        
        transformed = transcript_data.copy()
        transformed_results = transcript_data['results'].copy()
        
        # Transform transcripts to text
        if 'transcripts' in transformed_results:
            transformed_results['text'] = transformed_results.pop('transcripts')
        
        # Transform items
        if 'items' in transformed_results:
            transformed_items = []
            for item in transformed_results['items']:
                transformed_item = item.copy()
                
                # Rename start_time to start and end_time to end
                if 'start_time' in transformed_item:
                    transformed_item['start'] = transformed_item.pop('start_time')
                if 'end_time' in transformed_item:
                    transformed_item['end'] = transformed_item.pop('end_time')
                
                # Transform alternatives
                if 'alternatives' in transformed_item and isinstance(transformed_item['alternatives'], list):
                    transformed_alternatives = []
                    for alt in transformed_item['alternatives']:
                        transformed_alt = alt.copy()
                        # Rename content to text
                        if 'content' in transformed_alt:
                            transformed_alt['text'] = transformed_alt.pop('content')
                        transformed_alternatives.append(transformed_alt)
                    transformed_item['alternatives'] = transformed_alternatives
                
                transformed_items.append(transformed_item)
            transformed_results['items'] = transformed_items
        
        transformed['results'] = transformed_results
        return transformed

    def _parse_transcript_segments(self, transcript_data: dict) -> Dict[int, Dict[str, Any]]:
        """
        Parse transcript data from AWS Transcribe into segments.
        """
        segments = {}
        items = transcript_data.get('results', {}).get('items', [])
        
        if not items:
            # Fallback: use full transcript if no items
            full_text = transcript_data.get('results', {}).get('transcripts', [{}])[0].get('transcript', '')
            if full_text:
                segments[1] = {
                    "content": {
                        "TEXT": full_text,
                        "COMBINED": full_text,
                    },
                    "metadata": {
                        "extractor": "aws-transcribe",
                        "segment": 1,
                    },
                }
            return segments
        
        # Group items into segments (by speaker or time gaps)
        current_segment = []
        segment_num = 1
        last_end_time = 0.0
        segment_gap_threshold = 2.0  # 2 seconds gap = new segment
        
        for item in items:
            item_type = item.get('type')
            if item_type == 'pronunciation':
                # Safely convert start_time and end_time to float
                start_time_str = item.get('start_time')
                end_time_str = item.get('end_time')
                start_time = float(start_time_str) if start_time_str else 0.0
                end_time = float(end_time_str) if end_time_str else 0.0
                
                # Check if we should start a new segment
                if start_time - last_end_time > segment_gap_threshold and current_segment:
                    # Save current segment
                    words = [i.get('alternatives', [{}])[0].get('content', '') for i in current_segment]
                    text = ' '.join(words)
                    if text.strip():  # Only add non-empty segments
                        # Get timestamps from first and last items in segment
                        first_item_start = current_segment[0].get('start_time')
                        last_item_end = current_segment[-1].get('end_time')
                        start_ms = int(float(first_item_start) * 1000) if first_item_start else None
                        end_ms = int(float(last_item_end) * 1000) if last_item_end else None
                        
                        segments[segment_num] = {
                            "content": {
                                "TEXT": text,
                                "COMBINED": text,
                            },
                            "metadata": {
                                "extractor": "aws-transcribe",
                                "segment": segment_num,
                                "start_ms": start_ms,
                                "end_ms": end_ms,
                            },
                        }
                        segment_num += 1
                    current_segment = []
                
                current_segment.append(item)
                last_end_time = end_time
            elif item_type == 'punctuation':
                # Add punctuation to current segment if available
                if current_segment:
                    punctuation = item.get('alternatives', [{}])[0].get('content', '')
                    if punctuation:
                        # Append punctuation to the last word in current segment
                        if current_segment:
                            last_word = current_segment[-1]
                            last_word_alt = last_word.get('alternatives', [{}])[0]
                            last_word_alt['content'] = last_word_alt.get('content', '') + punctuation
        
        # Add final segment
        if current_segment:
            words = [i.get('alternatives', [{}])[0].get('content', '') for i in current_segment]
            text = ' '.join(words)
            if text.strip():  # Only add non-empty segments
                # Get timestamps from first and last items in segment
                first_item_start = current_segment[0].get('start_time')
                last_item_end = current_segment[-1].get('end_time')
                start_ms = int(float(first_item_start) * 1000) if first_item_start else None
                end_ms = int(float(last_item_end) * 1000) if last_item_end else None
                
                segments[segment_num] = {
                    "content": {
                        "TEXT": text,
                        "COMBINED": text,
                    },
                    "metadata": {
                        "extractor": "aws-transcribe",
                        "segment": segment_num,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                    },
                }
        
        # If no segments created, use full transcript
        if not segments:
            full_text = transcript_data.get('results', {}).get('transcripts', [{}])[0].get('transcript', '')
            if full_text:
                segments[1] = {
                    "content": {
                        "TEXT": full_text,
                        "COMBINED": full_text,
                    },
                    "metadata": {
                        "extractor": "aws-transcribe",
                        "segment": 1,
                    },
                }
        
        return segments

    @log_extractor_method()
    def read(self, file_path: str, **kwargs) -> Dict[int, Dict[str, Any]]:
        """
        Transcribe audio file using AWS Transcribe.
        AWS Transcribe requires files to be in S3, so we upload if needed.
        Returns segments with transcribed text.
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Generate unique job name
            job_name = f"transcribe-{uuid.uuid4().hex[:16]}"
            
            # Upload file to S3 if not already there
            file_extension = Path(file_path).suffix.lower()
            # AWS Transcribe supports: mp3, mp4, wav, flac, ogg, amr, webm
            supported_formats = ['.mp3', '.mp4', '.wav', '.flac', '.ogg', '.amr', '.webm']
            if file_extension not in supported_formats:
                raise ValueError(f"Unsupported audio format: {file_extension}. AWS Transcribe supports: {', '.join(supported_formats)}")
            
            s3_key = f"audio-transcriptions/{job_name}{file_extension}"
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            
            # Upload file to S3
            logger.info(f"Uploading {file_path} to S3: {s3_uri}")
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            
            # Start transcription job
            media_format = file_extension[1:]  # Remove the dot
            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': s3_uri},
                MediaFormat=media_format,
                LanguageCode='en-US',  # Default to English, can be made configurable
                Settings={
                    'ShowSpeakerLabels': False,
                    'ShowAlternatives': False
                }
            )
            
            # Poll for completion
            max_wait_time = 600  # 10 minutes
            poll_interval = 5  # 5 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    # Get transcript from S3
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    
                    # Download transcript JSON
                    with urllib.request.urlopen(transcript_uri) as url:
                        transcript_data = json.loads(url.read().decode())
                    
                    # Parse segments from transcript
                    segments = self._parse_transcript_segments(transcript_data)
                    
                    # Transform and store raw transcript_data in the first segment's metadata for later retrieval
                    if segments:
                        first_seg_num = min(segments.keys())
                        if first_seg_num in segments:
                            # Transform the data before storing
                            transformed_data = self._transform_transcript_data(transcript_data)
                            segments[first_seg_num]["metadata"]["raw_transcript_data"] = transformed_data
                    
                    # Clean up S3 file (optional - comment out if you want to keep files)
                    try:
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                    except Exception as e:
                        logger.warning(f"Could not delete S3 file {s3_key}: {e}")
                    
                    # Delete transcription job
                    try:
                        self.transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
                    except Exception as e:
                        logger.warning(f"Could not delete transcription job {job_name}: {e}")
                    
                    return segments
                    
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    raise RuntimeError(f"AWS Transcribe job failed: {failure_reason}")
                
                # Wait before next poll
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            
            # Timeout
            raise RuntimeError(f"Transcription job timed out after {max_wait_time} seconds")
            
        except Exception as e:
            logger.error(f"Error transcribing audio with AWS Transcribe: {e}")
            error_msg = f"Error transcribing audio: {str(e)}"
            return {
                1: {
                    "content": {
                        "TEXT": error_msg,
                        "COMBINED": error_msg,
                    },
                    "metadata": {
                        "extractor": "aws-transcribe",
                        "segment": 1,
                        "error": str(e),
                    },
                }
            }

    @log_extractor_method()
    def calculate_cost(self, duration_seconds: float, **kwargs) -> float:
        """
        Calculate cost for AWS Transcribe based on duration.
        """
        return self.cost_calculator.calculate_audio_cost(
            service_name="aws-transcribe",
            duration_seconds=duration_seconds,
            **kwargs
        )

    @log_extractor_method()
    def get_usage_metrics(self, file_path: str, **kwargs) -> dict:
        """
        Get usage metrics for AWS Transcribe.
        """
        try:
            import mutagen
            audio_file = mutagen.File(file_path)
            if audio_file is not None:
                duration_seconds = audio_file.info.length
                return {
                    "duration_seconds": duration_seconds,
                    "service": "aws-transcribe",
                    "estimated_cost": self.calculate_cost(duration_seconds, **kwargs)
                }
        except ImportError:
            # Fallback if mutagen not available
            pass
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
        
        return {
            "duration_seconds": 0.0,
            "service": "aws-transcribe",
            "estimated_cost": 0.0
        }

    @log_extractor_method()
    def supports_webhook(self) -> bool:
        return True  # AWS Transcribe supports webhooks via SNS

    @log_extractor_method()
    def get_status(self, job_id: str) -> str:
        """
        Check the status of a transcription job.
        """
        try:
            response = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_id
            )
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            # Map AWS statuses to our statuses
            status_map = {
                'IN_PROGRESS': 'running',
                'COMPLETED': 'succeeded',
                'FAILED': 'failed',
                'QUEUED': 'pending'
            }
            return status_map.get(status, 'pending')
        except ClientError as e:
            logger.error(f"Error getting transcription job status: {e}")
            return "failed"

    @log_extractor_method()
    def get_result(self, job_id: str) -> Union[str, Dict[str, Any]]:
        """
        Fetch the final parsed output for a job.
        """
        try:
            response = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_id
            )
            
            if response['TranscriptionJob']['TranscriptionJobStatus'] != 'COMPLETED':
                return {}
            
            # Get transcript from S3
            transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
            with urllib.request.urlopen(transcript_uri) as url:
                transcript_data = json.loads(url.read().decode())
            
            # Parse and return segments
            return self._parse_transcript_segments(transcript_data)
        except Exception as e:
            logger.error(f"Error getting transcription result: {e}")
            return {}

    @log_extractor_method()
    def handle_webhook(self, payload: dict) -> Union[str, Dict[str, Any]]:
        """
        Handle AWS Transcribe webhook payloads (via SNS).
        AWS Transcribe sends SNS notifications when jobs complete.
        """
        try:
            # SNS notification format
            if 'Type' in payload and payload['Type'] == 'Notification':
                message = json.loads(payload['Message'])
                job_name = message.get('TranscriptionJobName')
                status = message.get('TranscriptionJobStatus')
                
                if status == 'COMPLETED':
                    # Get result using job_name
                    return self.get_result(job_name)
                elif status == 'FAILED':
                    failure_reason = message.get('FailureReason', 'Unknown error')
                    return {
                        1: {
                            "content": {
                                "TEXT": f"AWS Transcribe error: {failure_reason}",
                                "COMBINED": f"AWS Transcribe error: {failure_reason}",
                            },
                            "metadata": {
                                "extractor": "aws-transcribe",
                                "segment": 1,
                                "error": failure_reason,
                            },
                        }
                    }
            
            return {}
        except Exception as e:
            logger.error(f"Error handling AWS Transcribe webhook: {e}")
            return {
                1: {
                    "content": {
                        "TEXT": f"Error processing webhook: {str(e)}",
                        "COMBINED": f"Error processing webhook: {str(e)}",
                    },
                    "metadata": {
                        "extractor": "aws-transcribe",
                        "segment": 1,
                        "error": str(e),
                    },
                }
            }

