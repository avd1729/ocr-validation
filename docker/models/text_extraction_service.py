from abc import ABC, abstractmethod

class TextExtractionService(ABC):
    @abstractmethod
    def extract_text_fields(self, image_bytes: bytes):
        pass

