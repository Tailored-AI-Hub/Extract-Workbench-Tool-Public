"""
Utility functions for audio extractors.
"""
from typing import Optional


def round_confidence(confidence: Optional[float]) -> Optional[float]:
    """
    Round confidence score to 2 decimal places.
    
    Args:
        confidence: Confidence score as float or None
        
    Returns:
        Rounded confidence score to 2 decimal places, or None if input is None/invalid
    """
    if confidence is None:
        return None
    try:
        return round(float(confidence), 2)
    except (ValueError, TypeError):
        return None

