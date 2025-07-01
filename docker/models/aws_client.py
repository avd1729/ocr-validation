import boto3
from models.document_validation_client import DocumentValidationClient
from models.text_extraction_service import TextExtractionService
from models.face_comparison_service import FaceComparisonService
from config.constants import REKOGNITION_THRESHOLD

class AWSTextExtractionService(TextExtractionService):
    def __init__(self):
        self.textract = boto3.client('textract')

    def extract_text_fields(self, image_bytes: bytes):
        result = self.textract.detect_document_text(Document={'Bytes': image_bytes})
        text = "\n".join(b["Text"] for b in result["Blocks"] if b["BlockType"] == "LINE")
        return text


class AWSFaceComparisonService(FaceComparisonService):
    def __init__(self):
        self.rekognition = boto3.client('rekognition')

    def compare_faces(self, source_image: bytes, target_image: bytes):
        response = self.rekognition.compare_faces(
            SourceImage = {'Bytes': source_image},
            TargetImage = {'Bytes': target_image},
            SimilarityThreshold = REKOGNITION_THRESHOLD
        )
        return response['FaceMatches'][0]['Similarity'] / 100.0 if response['FaceMatches'] else 0.0


class AWSClient(DocumentValidationClient):
    def __init__(self):
        super().__init__(
            text_service=AWSTextExtractionService(),
            face_service=AWSFaceComparisonService()
        )
