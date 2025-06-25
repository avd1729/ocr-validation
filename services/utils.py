import uuid
import time
from pypdf import PdfReader
from io import BytesIO
from services.config import MIN_PAGES_REQUIRED

def generate_application_id():
    return f"APP-{uuid.uuid4().hex[:8].upper()}"

def validate_pdf_file(file):
    if not file or not file.filename.endswith(".pdf"):
        return False, "Upload a PDF file"
    
    # # Move to the end of the stream and get size
    # file.stream.seek(0, 2)  # Seek to the end
    # size_bytes = file.stream.tell()

    # size_mb = size_bytes / (1024 * 1024)

    # if size_mb > 10:
    #     return False, "File size exceeds the maximum limit (10MB)"
    return True, None

def validate_pdf_pages(pdf_data):
    try:
        pdf_bytes = BytesIO(pdf_data)
        reader = PdfReader(pdf_bytes)
        if len(reader.pages) < MIN_PAGES_REQUIRED:
            return False, f"Need at least {MIN_PAGES_REQUIRED} pages"
        return True, None
    except Exception:
        return False, "Invalid PDF file"

def get_current_timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
