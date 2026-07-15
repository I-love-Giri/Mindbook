from abc import ABC, abstractmethod

from video_processor.models.transcript import Transcript


class BaseStorage(ABC):
    @abstractmethod
    def save(self, transcript: Transcript) -> None:
        """Save a transcript."""
        pass

    @abstractmethod
    def get(self, video_id: str):
        """Return a Transcript or None."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any database connections."""
        pass