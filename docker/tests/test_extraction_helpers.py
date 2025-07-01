from src.extraction_helpers import (
    extract_after_label,
    extract_fields_from_form,
    extract_fields_from_pan
)


def test_extract_after_label_found():
    text = "FULL NAME JOHN DOE"
    label_pattern = r"FULL NAME\s*"
    value_pattern = r"[A-Z ]+"
    result = extract_after_label(text, label_pattern, value_pattern)
    assert result == "JOHN DOE"

def test_extract_after_label_not_found():
    text = "OTHER NAME JANE"
    result = extract_after_label(text, r"FULL NAME\s*", r"[A-Z ]+")
    assert result is None

def test_extract_fields_from_form_full():
    text = """PAN NUMBER ABCDE1234F
              FULL NAME JOHN DOE
              DATE OF BIRTH 12/03/1990
              FATHER NAME MICHAEL DOE"""
    fields = extract_fields_from_form(text)
    assert fields["pan"] == "ABCDE1234F"
    assert fields["name"] == "JOHN DOE"
    assert fields["dob"] == "12/03/1990"
    assert fields["father_name"] == "MICHAEL DOE"


def test_extract_fields_from_pan_all_fields():
    text = """Permanent Account Number Card
              ABCDE1234F
              Name: JANE DOE
              Father's Name: JOHN DOE
              Date of Birth
              01/01/1980"""
    fields = extract_fields_from_pan(text)
    assert fields["pan"] == "ABCDE1234F"
    assert fields["name"] == "JANE DOE"
    assert fields["father_name"] == "JOHN DOE"
    assert fields["dob"] == "01/01/1980"

def test_extract_fields_from_pan_missing_fields():
    text = "Permanent Account Number Card ABCDE1234F"
    fields = extract_fields_from_pan(text)
    assert fields["pan"] == "ABCDE1234F"
    assert fields["name"] is None
    assert fields["father_name"] is None
    assert fields["dob"] is None
