import base64
import pytest
from unittest.mock import patch, MagicMock
from src.utils import parse_pdf
from config.constants import PAGES_REQUIRED
from src.utils import get_similarity_score
from src.utils import sanity_check

def test_exact_match():
    assert get_similarity_score("hello", "hello") == 100

def test_partial_match():
    assert get_similarity_score("hello", "helo") > 80

def test_mismatch():
    assert get_similarity_score("hello", "world") < 50

def test_none_or_empty():
    assert get_similarity_score("", "hello") == 0
    assert get_similarity_score(None, "hello") == 0

def test_valid_pdf_signature_and_mime(monkeypatch):
    valid_pdf = b'%PDF-1.4 rest of pdf data here'

    # Monkeypatch magic to return correct MIME
    monkeypatch.setattr("magic.from_buffer", lambda x, mime=True: "application/pdf")
    
    assert sanity_check(valid_pdf) is True

def test_invalid_pdf_signature(monkeypatch):
    invalid_pdf = b'NOTPDF rest of data'

    # Monkeypatch magic to return correct MIME anyway
    monkeypatch.setattr("magic.from_buffer", lambda x, mime=True: "application/pdf")

    assert sanity_check(invalid_pdf) is False

def test_invalid_pdf_mime(monkeypatch):
    valid_pdf = b'%PDF-1.4 some content'

    # Monkeypatch magic to return a wrong MIME type
    monkeypatch.setattr("magic.from_buffer", lambda x, mime=True: "text/plain")

    assert sanity_check(valid_pdf) is False

def test_completely_invalid_file(monkeypatch):
    garbage = b'abcdefg12345'

    # Monkeypatch to simulate wrong MIME type
    monkeypatch.setattr("magic.from_buffer", lambda x, mime=True: "image/png")

    assert sanity_check(garbage) is False


@pytest.fixture
def dummy_event():
    payload = b"%PDF-1.4 dummy content"
    encoded = base64.b64encode(payload).decode("utf-8")
    return {
        "httpMethod": "POST",
        "headers": {"Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary"},
        "body": encoded,
        "isBase64Encoded": True
    }

@patch("src.utils.PdfReader")
@patch("src.utils.FieldStorage")
@patch("src.utils.sanity_check", return_value=True)
def test_parse_pdf_success(mock_sanity, mock_field_storage, mock_pdf_reader, dummy_event):
    mock_file = MagicMock()
    mock_file.file.read.return_value = b"%PDF-1.4 dummy content"
    mock_field_storage.return_value = {'file': mock_file}

    mock_pdf_reader.return_value.pages = [1, 2, 3]

    result = parse_pdf(dummy_event)
    assert result == b"%PDF-1.4 dummy content"

@patch("src.utils.FieldStorage")
def test_parse_pdf_missing_file(mock_field_storage, dummy_event):
    mock_field_storage.return_value = {}
    with pytest.raises(Exception, match="Missing 'file' field in form"):
        parse_pdf(dummy_event)

@patch("src.utils.FieldStorage")
@patch("src.utils.sanity_check", return_value=False)
def test_parse_pdf_invalid_file_type(mock_sanity, mock_field_storage, dummy_event):
    mock_file = MagicMock()
    mock_file.file.read.return_value = b"Not a PDF"
    mock_field_storage.return_value = {'file': mock_file}

    with pytest.raises(Exception, match="Invalid file type"):
        parse_pdf(dummy_event)

@patch("src.utils.PdfReader")
@patch("src.utils.FieldStorage")
@patch("src.utils.sanity_check", return_value=True)
def test_parse_pdf_page_count_error(mock_sanity, mock_field_storage, mock_pdf_reader, dummy_event):
    mock_file = MagicMock()
    mock_file.file.read.return_value = b"%PDF-1.4 dummy content"
    mock_field_storage.return_value = {'file': mock_file}

    mock_pdf_reader.return_value.pages = [1]  # Only one page

    with pytest.raises(Exception, match=f"Need exactly {PAGES_REQUIRED} pages"):
        parse_pdf(dummy_event)

def test_parse_pdf_invalid_method():
    event = {"httpMethod": "GET", "headers": {}, "body": "", "isBase64Encoded": False}
    with pytest.raises(Exception, match="Only POST method Supported"):
        parse_pdf(event)
