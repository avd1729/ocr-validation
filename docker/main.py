import json
import uuid
import time
import asyncio

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_bytes
from src.utils import parse_pdf, get_similarity_score
from src.services import textract_process_sync, compare_faces_sync, extract_form_page_sync, prepare_images_sync

executor = ThreadPoolExecutor(max_workers=4)

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

            async def timed(name, func):
                start = time.time()
                result = await func()
                metrics[name] = round((time.time() - start) * 1000, 2)
                return result

            async def extract_form_page_data():
                return await loop.run_in_executor(executor, extract_form_page_sync, pdf_bytes1)

            async def extract_pan_card_data():
                def get_pan_data_textract():
                    img_bytes = convert_from_bytes(pdf_bytes2.read(), dpi=150, first_page=2, last_page=2)
                    buf = BytesIO()
                    img_bytes[0].convert("RGB").save(buf, format="JPEG", quality=75)
                    buf.seek(0)
                    return textract_process_sync(buf.read())
                return await loop.run_in_executor(executor, get_pan_data_textract)

            async def compare_faces():
                def run():
                    img2, img3 = prepare_images_sync(pdf_data)
                    if not img2 or not img3:
                        return None
                    return compare_faces_sync(img2, img3)
                return await loop.run_in_executor(executor, run)

            tasks = await asyncio.gather(
                timed("page1_ocr_ms", extract_form_page_data),
                timed("page2_textract_ms", extract_pan_card_data),
                timed("face_match_ms", compare_faces)
            )

            p1_data, p2_data, similarity = tasks

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
