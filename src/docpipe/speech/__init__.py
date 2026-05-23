"""Speech-to-text backends for docpipe."""

from docpipe.speech.service import TranscriptionService
from docpipe.speech.types import TranscribeResult, TranscriptionSegment

__all__ = [
    "TranscribeResult",
    "TranscriptionSegment",
    "TranscriptionService",
]
