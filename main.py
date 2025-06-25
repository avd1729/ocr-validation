import time
import asyncio
from quart import Quart, request, jsonify
from io import BytesIO

from services.utils import (
    generate_application_id, validate_pdf_file, 
    validate_pdf_pages, get_current_timestamp
)
from services.async_processors import (
    extract_page1_data, extract_page2_data_via_textract, compare_faces_async
)
from services.validators import validate_fields, validate_face_match

app = Quart(__name__)

@app.route("/validate", methods=["POST"])
async def validate_pdf():
    start_time = time.time()

    try:
        files = await request.files
        file = files.get("file")
        
        # Validate file
        is_valid, error = validate_pdf_file(file)
        if not is_valid:
            return jsonify({"error": error}), 400

        pdf_data = file.read()
        
        # Validate PDF pages
        is_valid, error = validate_pdf_pages(pdf_data)
        if not is_valid:
            return jsonify({"error": error}), 400

        parallel_start = time.time()
        
        pdf_bytes1 = BytesIO(pdf_data)
        pdf_bytes2 = BytesIO(pdf_data)
        
        # Run all tasks concurrently
        results = await asyncio.gather(
            extract_page1_data(pdf_bytes1),
            extract_page2_data_via_textract(pdf_bytes2),
            compare_faces_async(pdf_data),
            return_exceptions=True
        )
        
        parallel_end = time.time()
        
        # Extract results
        page1_data, page1_time = results[0] if not isinstance(results[0], Exception) else ({}, 0)
        page2_data, page2_time = results[1] if not isinstance(results[1], Exception) else ({}, 0)
        similarity, face_time = results[2] if not isinstance(results[2], Exception) else (None, 0)

        # Validate fields
        field_scores, field_pass, field_errors = validate_fields(page1_data, page2_data)
        
        # Validate face match
        face_pass, face_error = validate_face_match(similarity)
        
        # Collect all errors
        errors = field_errors
        if face_error:
            errors.append(face_error)

        # Calculate metrics
        total_time = time.time() - start_time
        metrics = {
            "page1_ocr_ms": page1_time,
            "page2_textract_ms": page2_time,
            "face_match_ms": face_time,
            "ocr_ms": page1_time + page2_time,
            "parallel_processing_ms": int((parallel_end - parallel_start) * 1000),
            "total_processing_ms": int(total_time * 1000),
            "total_processing_seconds": round(total_time, 2)
        }

        result = {
            "application_id": generate_application_id(),
            "field_matches": field_scores,
            "field_pass": field_pass,
            "face_match": {
                "similarity": round(similarity, 2) if similarity is not None else None,
                "pass": face_pass
            },
            "overall_pass": field_pass and face_pass,
            "errors": errors,
            "processed_at": get_current_timestamp(),
            "metrics": metrics
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
async def health_check():
    return jsonify({
        "status": "healthy", 
        "timestamp": get_current_timestamp()
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)