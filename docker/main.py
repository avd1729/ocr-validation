import json
import uuid
import time
import asyncio
from src.utils import timed
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_bytes
from src.utils import parse_pdf, get_similarity_score
from src.services import text_extract_process_sync, compare_faces_sync, extract_form_page_sync, prepare_images_sync
from config.constants import PDF_DPI, IMAGE_QUALITY, SIMILARITY_THRESHOLD, MAX_WORKERS, FACE_SIMILARITY_THRESHOLD

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def handler(event, context):
    try:
        start_time = time.time()
        # Parse PDF file
        try:
            pdf_data = parse_pdf(event)
        except Exception as e:
            return {"statusCode": 400, "body": json.dumps({"error": f"Invalid PDF: {str(e)}"})}

        # Async tasks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def process():
            pdf_bytes1 = BytesIO(pdf_data)
            pdf_bytes2 = BytesIO(pdf_data)

            metrics = {}

            async def extract_form_page_data():
                return await loop.run_in_executor(executor, extract_form_page_sync, pdf_bytes1)

            async def extract_pan_card_data():
                def get_pan_text_extract():
                    img_bytes = convert_from_bytes(pdf_bytes2.read(), dpi=PDF_DPI, first_page=2, last_page=2)
                    buf = BytesIO()
                    img_bytes[0].convert("RGB").save(buf, format="JPEG", quality=IMAGE_QUALITY)
                    buf.seek(0)
                    return text_extract_process_sync(buf.read())
                return await loop.run_in_executor(executor, get_pan_text_extract)

            async def compare_faces():
                def run():
                    pan_image, selfie_image = prepare_images_sync(pdf_data)
                    if not pan_image or not selfie_image:
                        return None
                    return compare_faces_sync(pan_image, selfie_image)
                return await loop.run_in_executor(executor, run)

            tasks = await asyncio.gather(
                timed(metrics, "page1_ocr_ms", extract_form_page_data),
                timed(metrics, "page2_text_extract_ms", extract_pan_card_data),
                timed(metrics, "face_match_ms", compare_faces)
            )

            form_page_data, pan_card_data, face_match_similarity = tasks

            # Match logic
            fields = ["name", "father_name", "dob", "pan"]
            field_scores = {}
            field_pass = True
            errors = []

            for field in fields:
                score = get_similarity_score(form_page_data.get(field), pan_card_data.get(field))
                passed = score >= SIMILARITY_THRESHOLD 
                field_scores[field] = {
                    "score": score,
                    "pass": passed,
                    "page1_value": form_page_data.get(field),
                    "page2_value": pan_card_data.get(field)
                }
                if not passed:
                    field_pass = False
                    errors.append({
                        "code": f"{field.upper()}_MISMATCH",
                        "message": f"{field.replace('_', ' ').title()} differs between Page 1 and PAN card"
                    })

            face_pass = face_match_similarity is not None and face_match_similarity >= FACE_SIMILARITY_THRESHOLD
            if face_match_similarity is None:
                errors.append({"code": "FACE_MATCH_ERROR", "message": "Could not process face comparison"})

            metrics["total_processing_seconds"] = round(time.time() - start_time, 2)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "application_id": f"APP-{uuid.uuid4().hex[:8].upper()}",
                    "field_matches": field_scores,
                    "field_pass": field_pass,
                    "face_match": {
                        "similarity": round(face_match_similarity, 2) if face_match_similarity else None,
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
