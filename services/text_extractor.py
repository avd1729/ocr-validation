import re
from pypdf import PdfReader

def extract_after_label(text, label_pattern, value_pattern):
    pattern = re.compile(label_pattern + "(" + value_pattern + ")", re.IGNORECASE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None

def extract_fields_page1(text):
    text = re.sub(r"[ ]{2,}", " ", text)
    joined = "\n".join(text.splitlines())
    fields = {
        "pan": extract_after_label(joined, r"PAN NUMBER\s*", r"[A-Z]{5}[0-9]{4}[A-Z]"),
        "name": extract_after_label(joined, r"FULL NAME\s*", r"[A-Z ]+"),
        "dob": extract_after_label(joined, r"DATE OF BIRTH.*?\s*", r"\d{2}[-/]\d{2}[-/]\d{4}"),
    }
    father_match = re.search(r"FATHER\s+NAME[\s\n]*([A-Z]+)[\s\n]*([A-Z]+)", joined)
    if father_match:
        fields["father_name"] = f"{father_match.group(1)} {father_match.group(2)}"
    else:
        fields["father_name"] = extract_after_label(joined, r"FATHER\s+NAME", r"[A-Z\s]+")
    return fields

def extract_fields_page2(text):
    return {
        "pan": extract_after_label(text, r"Permanent Account Number Card\s*", r"[A-Z]{5}[0-9]{4}[A-Z]"),
        "name": extract_after_label(text, r"Name\s*[:\-]?\s*", r"[A-Z ]+"),
        "father_name": extract_after_label(text, r"Father'?s Name\s*[:\-]?\s*", r"[A-Z ]+"),
        "dob": extract_after_label(text, r"Date of Birth\s*[:\-]?\s*", r"\d{2}[-/]\d{2}[-/]\d{4}")
    }

def extract_page1_sync(pdf_bytes):
    try:
        reader = PdfReader(pdf_bytes)
        page1_text = reader.pages[0].extract_text()
        return extract_fields_page1(page1_text)
    except Exception as e:
        print("Page 1 extraction error:", e)
        return {}