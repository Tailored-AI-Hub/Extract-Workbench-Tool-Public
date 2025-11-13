from typing import Union, Optional
from abc import ABC, abstractmethod

class AudioExtractorInterface(ABC):
    """
    Interface for audio extractors.
    Defines the contract that all audio extractors must implement.
    """

    @abstractmethod
    def get_information(self) -> dict:
        """
        Get information about the extractor.
        Returns:
            dict: Contains 'name', 'type', 'supports', 'description'
        """
        pass
    
    @abstractmethod
    def read(self, file_path: str, **kwargs) -> dict:
        """
        Extract/transcribe audio from a file.
        Returns a dictionary mapping segment numbers to content.
        """
        pass

    @abstractmethod
    def supports_webhook(self) -> bool:
        """
        Return True if the provider supports webhook callbacks.
        False for local extractors or APIs without webhook support.
        """
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> str:
        """
        For async APIs, check the processing status.
        Returns one of: ['pending', 'running', 'succeeded', 'failed'].
        For sync extractors, return 'succeeded' immediately.
        """
        pass

    @abstractmethod
    def get_result(self, job_id: str) -> Union[str, dict]:
        """
        Fetch the final parsed output once status == succeeded.
        For sync extractors, this returns the immediate output from `read`.
        """
        pass

    @abstractmethod
    def handle_webhook(self, payload: dict) -> Union[str, dict]:
        """
        Process an incoming webhook payload (for async providers that push results).
        Return standardized parsed output.
        No-op for sync extractors.
        """
        pass

    @abstractmethod
    def calculate_cost(self, duration_seconds: float, api_response: Optional[dict] = None) -> float:
        """
        Calculate extraction cost based on audio duration and API response.
        
        Args:
            duration_seconds: Length of audio in seconds
            api_response: Optional API response containing cost information
            
        Returns:
            float: Calculated cost in USD
        """
        pass

    @abstractmethod
    def get_usage_metrics(self, api_response: Optional[dict] = None) -> dict:
        """
        Extract usage metrics from API response for cost verification.
        
        Args:
            api_response: Optional API response containing usage information
            
        Returns:
            dict: Usage metrics (duration_seconds, tokens, etc.)
        """
        pass