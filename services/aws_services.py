import boto3
# from pypdf import PdfReader, PdfWriter
from io import BytesIO
from pdf2image import convert_from_bytes
import time

textract = boto3.client('textract')
rekognition = boto3.client('rekognition')



def textract_process_sync(page_bytes):
    try:
        start_time = time.time()
        
        textract_result = textract.detect_document_text(Document={'Bytes': page_bytes})
        
        end_time = time.time()
        print(f"Textract API call took: {round(end_time - start_time, 2)} seconds")

        page2_text = "\n".join(
            b["Text"] for b in textract_result["Blocks"] if b["BlockType"] == "LINE"
        )

        from services.text_extractor import extract_fields_page2
        return extract_fields_page2(page2_text)
        
    except Exception as e:
        print("Textract error:", e)
        return {}


def compare_faces_sync(source, target):
    try:
        from services.config import REKOGNITION_THRESHOLD
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source},
            TargetImage={'Bytes': target},
            SimilarityThreshold=REKOGNITION_THRESHOLD
        )
        return response['FaceMatches'][0]['Similarity'] / 100.0 if response['FaceMatches'] else 0.0
    except Exception as e:
        print("Rekognition error:", e)
        return None

def extract_page2_via_textract(pdf_bytes):
    try:
        pdf_bytes.seek(0)
        
        images = convert_from_bytes(pdf_bytes.read(), dpi=150, first_page=2, last_page=2)
        
        # Compress the image
        img_buf = BytesIO()
        images[0].convert("RGB").save(img_buf, format="JPEG", quality=70)
        img_buf.seek(0)

        return textract_process_sync(img_buf.read())

    except Exception as e:
        print("Textract image preparation error:", e)
        return {}
