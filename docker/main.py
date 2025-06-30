import cgi
import io
import re
import json
import uuid
import time
import base64
import asyncio
import boto3

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from difflib import SequenceMatcher
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor

# AWS Clients
textract = boto3.client('textract')
rekognition = boto3.client('rekognition')
executor = ThreadPoolExecutor(max_workers=4)

def parse_multipart(event):
    content_type = event['headers'].get('Content-Type') or event['headers'].get('content-type')
    body = base64.b64decode(event['body']) if event['isBase64Encoded'] else event['body'].encode()

    fp = io.BytesIO(body)
    environ = {'REQUEST_METHOD': 'POST'}
    headers = {'content-type': content_type}
    fs = cgi.FieldStorage(fp=fp, environ=environ, headers=headers, keep_blank_values=True)

    if 'file' not in fs:
        raise Exception("Missing 'file' field in form")

    uploaded_file = fs['file']
    return uploaded_file.file.read()

# ------------------ Extraction Helpers ------------------

def extract_after_label(text, label_pattern, value_pattern):
    pattern = re.compile(label_pattern + "(" + value_pattern + ")", re.IGNORECASE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None

def extract_fields_page1(text):
    text = re.sub(r"[ ]{2,}", " ", text)
    joined = "\n".join(text.splitlines())
    fields = {
        "pan": extract_after_label(joined, r"PAN NUMBER\s*", r"[A-Z]{5}[0-9]{4}[A-Z]"),
        "name": extract_after_label(joined, r"FULL NAME\s*", r"[A-Z ]+"),
        "dob": extract_after_label(joined, r"DATE OF BIRTH.*?\s*", r"\d{2}[-/]\d{2}[-/]\d{4}"),
    }
    father_match = re.search(r"FATHER\s+NAME[\s\n]*([A-Z]+)[\s\n]*([A-Z]+)", joined)
    if father_match:
        fields["father_name"] = f"{father_match.group(1)} {father_match.group(2)}"
    else:
        fields["father_name"] = extract_after_label(joined, r"FATHER\s+NAME", r"[A-Z\s]+")
    return fields

def extract_fields_page2(text):
    return {
        "pan": extract_after_label(text, r"Permanent Account Number Card\s*", r"[A-Z]{5}[0-9]{4}[A-Z]"),
        "name": extract_after_label(text, r"Name\s*[:\-]?\s*", r"[A-Z ]+"),
        "father_name": extract_after_label(text, r"Father'?s Name\s*[:\-]?\s*", r"[A-Z ]+"),
        "dob": extract_after_label(text, r"Date of Birth\s*[:\-]?\s*", r"\d{2}[-/]\d{2}[-/]\d{4}")
    }

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

def get_similarity_score(a, b):
    if not a or not b:
        return 0
    return round(SequenceMatcher(None, a.strip(), b.strip()).ratio() * 100)

def handler(event, context):
    try:
        start_time = time.time()

        if event.get("httpMethod") != "POST":
            return {"statusCode": 405, "body": json.dumps({"error": "Only POST supported"})}

        # Parse PDF file from multipart
        try:
            pdf_data = parse_multipart(event)
            pdf_bytes = io.BytesIO(pdf_data)
            reader = PdfReader(pdf_bytes)
            if len(reader.pages) < 3:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Need at least 3 pages"})
                }
        except Exception as e:
            return {"statusCode": 400, "body": json.dumps({"error": f"Invalid PDF: {str(e)}"})}

        # Async tasks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process():
            pdf_bytes1 = io.BytesIO(pdf_data)
            pdf_bytes2 = io.BytesIO(pdf_data)

            metrics = {}

            async def timed(name, func):
                start = time.time()
                result = await func()
                metrics[name] = round((time.time() - start) * 1000, 2)  # in ms
                return result

            async def extract_page1_data():
                return await loop.run_in_executor(executor, extract_page1_sync, pdf_bytes1)

            async def extract_page2_data():
                def get_page2_textract():
                    img_bytes = convert_from_bytes(pdf_bytes2.read(), dpi=150, first_page=2, last_page=2)
                    buf = io.BytesIO()
                    img_bytes[0].convert("RGB").save(buf, format="JPEG", quality=75)
                    buf.seek(0)
                    return textract_process_sync(buf.read())
                return await loop.run_in_executor(executor, get_page2_textract)

            async def compare_faces():
                def run():
                    img2, img3 = prepare_images_sync(pdf_data)
                    if not img2 or not img3:
                        return None
                    return compare_faces_sync(img2, img3)
                return await loop.run_in_executor(executor, run)

            # Run tasks with timing
            p1_data = await timed("page1_ocr_ms", extract_page1_data)
            p2_data = await timed("page2_textract_ms", extract_page2_data)
            similarity = await timed("face_match_ms", compare_faces)

            # Match logic
            fields = ["name", "father_name", "dob", "pan"]
            field_scores = {}
            field_pass = True
            errors = []

            for f in fields:
                score = get_similarity_score(p1_data.get(f), p2_data.get(f))
                passed = score >= 80
                field_scores[f] = {
                    "score": score,
                    "pass": passed,
                    "page1_value": p1_data.get(f),
                    "page2_value": p2_data.get(f)
                }
                if not passed:
                    field_pass = False
                    errors.append({
                        "code": f"{f.upper()}_MISMATCH",
                        "message": f"{f.replace('_', ' ').title()} differs between Page 1 and PAN card"
                    })

            face_pass = similarity is not None and similarity >= 0.7
            if similarity is None:
                errors.append({"code": "FACE_MATCH_ERROR", "message": "Could not process face comparison"})

            metrics["total_processing_seconds"] = round(time.time() - start_time, 2)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "application_id": f"APP-{uuid.uuid4().hex[:8].upper()}",
                    "field_matches": field_scores,
                    "field_pass": field_pass,
                    "face_match": {
                        "similarity": round(similarity, 2) if similarity else None,
                        "pass": face_pass
                    },
                    "overall_pass": field_pass and face_pass,
                    "errors": errors,
                    "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "metrics": metrics
                })
            }


        return loop.run_until_complete(process())

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
