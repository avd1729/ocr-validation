import boto3
from pypdf import PdfReader, PdfWriter
from io import BytesIO

textract = boto3.client('textract')
rekognition = boto3.client('rekognition')

def textract_process_sync(page_bytes):
    try:
        textract_result = textract.detect_document_text(Document={'Bytes': page_bytes})
        page2_text = "\n".join(b["Text"] for b in textract_result["Blocks"] if b["BlockType"] == "LINE")
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
    pdf_bytes.seek(0)
    writer = PdfWriter()
    writer.add_page(PdfReader(pdf_bytes).pages[1])
    page2_buf = BytesIO()
    writer.write(page2_buf)
    page2_buf.seek(0)
    return textract_process_sync(page2_buf.read())