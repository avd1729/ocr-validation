from abc import ABC
from typing import Optional
from models.text_extraction_service import TextExtractionService
from models.face_comparison_service import FaceComparisonService


class DocumentValidationClient(ABC):
    def __init__(self, text_service: TextExtractionService, face_service: FaceComparisonService):
        self.text_service = text_service
        self.face_service = face_service

    def extract_fields(self, image_bytes: bytes) -> str:
        return self.text_service.extract_text_fields(image_bytes)

    def compare(self, source_image: bytes, target_image: bytes) -> Optional[float]:
        return self.face_service.compare_faces(source_image, target_image)
