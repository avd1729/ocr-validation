import re

def extract_after_label(text: str, label_pattern: str, value_pattern: str):
    pattern = re.compile(label_pattern + "(" + value_pattern + ")", re.IGNORECASE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None

def extract_fields_from_form(text: str):
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

def extract_fields_from_pan(text: str):
    dob_match = re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{4}", text)
    dob = dob_match.group(0) if dob_match else None

    return {
        "pan": extract_after_label(text, r"Permanent Account Number Card\s*", r"[A-Z]{5}[0-9]{4}[A-Z]"),
        "name": extract_after_label(text, r"Name\s*[:\-]?\s*", r"[A-Z ]+"),
        "father_name": extract_after_label(text, r"Father'?s Name\s*[:\-]?\s*", r"[A-Z ]+"),
        "dob": dob
    }