from io import BytesIO
from unittest.mock import patch, MagicMock
from src.services import (
    text_extract_process_sync,
    compare_faces_sync,
    extract_form_page_sync,
    prepare_images_sync
)

PDF_DUMMY = b"%PDF-1.4 dummy data for testing"
DUMMY_IMAGE_BYTES = b"\xff\xd8\xff"

@patch("src.services.text_service.extract_text_fields")
@patch("src.services.extract_fields_from_pan")
def test_text_extract_process_sync(mock_extract_pan, mock_text_service):
    mock_text_service.return_value = {"text": "dummy text"}
    mock_extract_pan.return_value = {"pan": "ABCDE1234F"}

    result = text_extract_process_sync(b"fake-pdf")
    assert result == {"pan": "ABCDE1234F"}
    mock_text_service.assert_called_once()

@patch("src.services.face_service.compare_faces")
def test_compare_faces_sync(mock_compare):
    mock_compare.return_value = 0.9
    result = compare_faces_sync(b"source", b"target")
    assert result == 0.9
    mock_compare.assert_called_once_with(b"source", b"target")

@patch("src.services.PdfReader")
@patch("src.services.extract_fields_from_form")
def test_extract_form_page_sync(mock_extract, mock_reader):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Form Text"
    mock_reader.return_value.pages = [mock_page]
    mock_extract.return_value = {"name": "John Doe"}

    result = extract_form_page_sync(BytesIO(PDF_DUMMY))
    assert result == {"name": "John Doe"}
    mock_extract.assert_called_once_with("Form Text")

@patch("src.services.convert_from_bytes")
def test_prepare_images_sync_success(mock_convert):
    mock_img = MagicMock()
    mock_img.convert.return_value.save = MagicMock()

    mock_convert.return_value = [mock_img, mock_img]
    img1, img2 = prepare_images_sync(PDF_DUMMY)
    
    assert isinstance(img1, bytes)
    assert isinstance(img2, bytes)

@patch("src.services.convert_from_bytes")
def test_prepare_images_sync_fail(mock_convert):
    mock_convert.return_value = [MagicMock()]  # Only 1 image
    img1, img2 = prepare_images_sync(PDF_DUMMY)
    assert img1 is None and img2 is None
