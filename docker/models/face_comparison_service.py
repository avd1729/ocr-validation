from abc import ABC, abstractmethod
from typing import Optional

class FaceComparisonService(ABC):
    @abstractmethod
    def compare_faces(self, source_image: bytes, target_image: bytes) -> Optional[float]:
        pass