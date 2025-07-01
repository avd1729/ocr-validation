import io
import magic
import base64
import cgi
from pypdf import PdfReader
from difflib import SequenceMatcher

def get_similarity_score(a, b):
    if not a or not b:
        return 0
    return round(SequenceMatcher(None, a.strip(), b.strip()).ratio() * 100)

def sanity_check(file_bytes: bytes):
    if not file_bytes.startswith(b'%PDF-'):
        return False
    
    mime = magic.from_buffer(file_bytes, mime=True)
    return mime == "application/pdf"

def parse_pdf(event):
    if event.get("httpMethod") != "POST":
        raise Exception("Only POST method Supported")

    content_type = event['headers'].get('Content-Type') or event['headers'].get('content-type')
    body = base64.b64decode(event['body']) if event['isBase64Encoded'] else event['body'].encode()

    fp = io.BytesIO(body)
    environ = {'REQUEST_METHOD': 'POST'}
    headers = {'content-type': content_type}
    fs = cgi.FieldStorage(fp=fp, environ=environ, headers=headers, keep_blank_values=True)

    if 'file' not in fs:
        raise Exception("Missing 'file' field in form")

    uploaded_file = fs['file']
    file_data = uploaded_file.file.read()

    if not sanity_check(file_data):
        raise Exception("Invalid file type")

    pdf_bytes = io.BytesIO(file_data)
    reader = PdfReader(pdf_bytes)
    
    if len(reader.pages) != 3:
        raise Exception("Need exactly 3 pages")

    return file_data
