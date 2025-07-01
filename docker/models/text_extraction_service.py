from abc import ABC, abstractmethod
from typing import Dict

class TextExtractionService(ABC):
    @abstractmethod
    def extract_text_fields(self, image_bytes: bytes) -> Dict[str, str]:
        pass

