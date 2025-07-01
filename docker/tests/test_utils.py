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
