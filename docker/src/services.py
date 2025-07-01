from io import BytesIO
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from src.extraction_helpers import extract_fields_from_form, extract_fields_from_pan
from models.aws_client import AWSClient
from config.constants import IMAGE_QUALITY

client = AWSClient() 
text_service = client.text_service
face_service = client.face_service

def text_extract_process_sync(page_bytes: bytes):
    result = text_service.extract_text_fields(page_bytes)
    return extract_fields_from_pan(result)


def compare_faces_sync(source: bytes, target: bytes):
    return face_service.compare_faces(source, target)

def extract_form_page_sync(pdf_bytes: bytes):
    reader = PdfReader(pdf_bytes)
    page1_text = reader.pages[0].extract_text()
    return extract_fields_from_form(page1_text)

def prepare_images_sync(pdf_data: bytes):
    images = convert_from_bytes(pdf_data, dpi=100, first_page=2, last_page=3)
    if len(images) < 2:
        return None, None

    pan_image = BytesIO()
    selfie_image = BytesIO()
    images[0].convert("RGB").save(pan_image, format="JPEG", quality=IMAGE_QUALITY)
    images[1].convert("RGB").save(selfie_image, format="JPEG", quality=IMAGE_QUALITY)

    return pan_image.getvalue(), selfie_image.getvalue()