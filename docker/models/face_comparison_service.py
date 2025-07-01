from abc import ABC, abstractmethod

class FaceComparisonService(ABC):
    @abstractmethod
    def compare_faces(self, source_image: bytes, target_image: bytes):
        pass