import os
import re
import json
import uuid
import time
import boto3
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from io import BytesIO
from difflib import SequenceMatcher
from pypdf import PdfReader
from pdf2image import convert_from_bytes
from PIL import Image
from mangum import Mangum

app = FastAPI()

# AWS Clients
textract = boto3.client('textract')
rekognition = boto3.client('rekognition')
executor = ThreadPoolExecutor(max_workers=4)

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
        start = time.time()
        textract_result = textract.detect_document_text(Document={'Bytes': page_bytes})
        print(f"Textract API call took {round(time.time() - start, 2)} seconds")
        page2_text = "\n".join(b["Text"] for b in textract_result["Blocks"] if b["BlockType"] == "LINE")
        return extract_fields_page2(page2_text)
    except Exception as e:
        print("Textract error:", e)
        return {}

def compare_faces_sync(source, target):
    try:
        response = rekognition.compare_faces(
            SourceImage={'Bytes': source},
            TargetImage={'Bytes': target},
            SimilarityThreshold=70
        )
        return response['FaceMatches'][0]['Similarity'] / 100.0 if response['FaceMatches'] else 0.0
    except Exception as e:
        print("Rekognition error:", e)
        return None

def extract_page1_sync(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        page1_text = reader.pages[0].extract_text()
        return extract_fields_page1(page1_text)
    except Exception as e:
        print("Page 1 extraction error:", e)
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

        img2.seek(0)
        img3.seek(0)

        return img2.read(), img3.read()
    except Exception as e:
        print("Image preparation error:", e)
        return None, None

# ------------------ Async Task Wrappers ------------------

async def extract_page1_data(pdf_bytes):
    start_time = time.time()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, extract_page1_sync, pdf_bytes)
    end_time = time.time()
    return result, int((end_time - start_time) * 1000)

async def extract_page2_data_via_textract(pdf_bytes):
    """Convert Page 2 to compressed image and send to Textract"""
    start_time = time.time()

    def process_page2():
        try:
            pdf_bytes.seek(0)
            images = convert_from_bytes(pdf_bytes.read(), dpi=150, first_page=2, last_page=2)
            if not images:
                print("No image generated for page 2.")
                return {}

            img_buf = BytesIO()
            images[0].convert("RGB").save(img_buf, format="JPEG", quality=75)
            img_buf.seek(0)

            return textract_process_sync(img_buf.read())
        except Exception as e:
            print("Textract page 2 image processing error:", e)
            return {}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_page2)
    end_time = time.time()
    return result, int((end_time - start_time) * 1000)

async def compare_faces_async(pdf_data):
    start_time = time.time()

    def process_faces():
        img2_bytes, img3_bytes = prepare_images_sync(pdf_data)
        if img2_bytes is None or img3_bytes is None:
            return None
        return compare_faces_sync(img2_bytes, img3_bytes)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_faces)
    end_time = time.time()
    return result, int((end_time - start_time) * 1000)

# ------------------ Utility ------------------

def get_similarity_score(a, b):
    if not a or not b:
        return 0
    return round(SequenceMatcher(None, a.strip(), b.strip()).ratio() * 100)

# ------------------ Routes ------------------

@app.post("/validate")
async def validate_pdf(file: UploadFile = File(...)):
    start_time = time.time()
    errors = []
    metrics = {}

    try:
        if not file.filename or not file.filename.endswith(".pdf"):
            return JSONResponse(
                status_code=400,
                content={"error": "Upload a PDF file"}
            )

        pdf_data = await file.read()
        pdf_bytes = BytesIO(pdf_data)

        # Check if PDF has at least 3 pages
        try:
            reader = PdfReader(pdf_bytes)
            if len(reader.pages) < 3:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Need at least 3 pages"}
                )
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid PDF file"}
            )

        parallel_start = time.time()

        # Duplicate stream
        pdf_bytes1 = BytesIO(pdf_data)
        pdf_bytes2 = BytesIO(pdf_data)

        # Run all 3 tasks concurrently
        results = await asyncio.gather(
            extract_page1_data(pdf_bytes1),
            extract_page2_data_via_textract(pdf_bytes2),
            compare_faces_async(pdf_data),
            return_exceptions=True
        )

        parallel_end = time.time()

        # Handle results and timings
        page1_data, page1_time = results[0] if not isinstance(results[0], Exception) else ({}, 0)
        page2_data, page2_time = results[1] if not isinstance(results[1], Exception) else ({}, 0)
        similarity, face_time = results[2] if not isinstance(results[2], Exception) else (None, 0)

        metrics.update({
            "page1_ocr_ms": page1_time,
            "page2_textract_ms": page2_time,
            "face_match_ms": face_time,
            "ocr_ms": page1_time + page2_time,
            "parallel_processing_ms": int((parallel_end - parallel_start) * 1000),
        })

        # Field matching
        fields = ["name", "father_name", "dob", "pan"]
        field_scores = {}
        field_pass = True

        for f in fields:
            score = get_similarity_score(page1_data.get(f), page2_data.get(f))
            passed = score >= 80
            field_scores[f] = {
                "score": score,
                "pass": passed,
                "page1_value": page1_data.get(f),
                "page2_value": page2_data.get(f)
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

        total_time = time.time() - start_time

        return {
            "application_id": f"APP-{uuid.uuid4().hex[:8].upper()}",
            "field_matches": field_scores,
            "field_pass": field_pass,
            "face_match": {
                "similarity": round(similarity, 2) if similarity is not None else None,
                "pass": face_pass
            },
            "overall_pass": field_pass and face_pass,
            "errors": errors,
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metrics": {
                **metrics,
                "total_processing_ms": int(total_time * 1000),
                "total_processing_seconds": round(total_time, 2)
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
def health():
    return {"status": "ok"}

# Lambda handler
handler = Mangum(app)
