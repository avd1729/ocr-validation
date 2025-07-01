import base64
import json

from main import handler

def load_test_pdf_bytes():
    with open("tests/assets/sample.pdf", "rb") as f:
        return f.read()

def encode_multipart(file_bytes: bytes, boundary="----WebKitFormBoundary7MA4YWxkTrZu0gW"):
    filename = "sample.pdf"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    
    return body, f"multipart/form-data; boundary={boundary}"

def test_handler_integration():
    pdf_bytes = load_test_pdf_bytes()
    body, content_type = encode_multipart(pdf_bytes)

    event = {
        "httpMethod": "POST",
        "headers": {
            "Content-Type": content_type
        },
        "body": base64.b64encode(body).decode(),
        "isBase64Encoded": True
    }

    response = handler(event, None)
    assert response["statusCode"] == 200

    body_json = json.loads(response["body"])
    assert "application_id" in body_json
    assert "field_matches" in body_json
    assert "face_match" in body_json
    assert "metrics" in body_json
