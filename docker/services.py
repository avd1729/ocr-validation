import boto3
from io import BytesIO
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from extraction_helpers import extract_fields_page1, extract_fields_page2

textract = boto3.client('textract')
rekognition = boto3.client('rekognition')

def textract_process_sync(page_bytes):
    try:
        result = textract.detect_document_text(Document={'Bytes': page_bytes})
        text = "\n".join(b["Text"] for b in result["Blocks"] if b["BlockType"] == "LINE")
        return extract_fields_page2(text)
    except Exception:
        return {}

def compare_faces_sync(source, target):
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source},
            TargetImage={'Bytes': target},
            SimilarityThreshold=70
        )
        return response['FaceMatches'][0]['Similarity'] / 100.0 if response['FaceMatches'] else 0.0
    except Exception:
        return None

def extract_page1_sync(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        page1_text = reader.pages[0].extract_text()
        return extract_fields_page1(page1_text)
    except Exception:
        return {}

def prepare_images_sync(pdf_data):
    try:
        images = convert_from_bytes(pdf_data, dpi=100, first_page=2, last_page=3)
        if len(images) < 2:
            return None, None

        img2 = BytesIO()
        img3 = BytesIO()

        images[0].convert("RGB").save(img2, format="JPEG", quality=75)
        images[1].convert("RGB").save(img3, format="JPEG", quality=75)

        return img2.getvalue(), img3.getvalue()
    except Exception:
        return None, None